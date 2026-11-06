"""PID speed-control simulation. Python 3.10+, standard library only."""
import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    kp: float = 2.0
    ki: float = 1.0
    kd: float = 0.1
    target: float = 1.0
    tau: float = 1.0
    duration: float = 12.0
    dt: float = 0.01
    limit: float = 3.0
    load: float = 0.3
    load_at: float = 6.0

    def validate(self):
        if not all(math.isfinite(x) for x in vars(self).values()):
            raise ValueError('All parameters must be finite')
        if min(self.tau, self.duration, self.dt, self.limit) <= 0:
            raise ValueError('tau, duration, dt and limit must be positive')
        if min(self.kp, self.ki, self.kd, self.target, self.load, self.load_at) < 0:
            raise ValueError('Gains, target, load and load_at must be nonnegative')
        if self.dt > self.tau / 10:
            raise ValueError('Use dt <= tau/10 for adequate sampling')
        if self.duration / self.dt > 200_000:
            raise ValueError('Simulation is limited to 200,000 steps')


def simulate(config):
    """Return (time, target, speed, command, load) sampled before each step."""
    config.validate()
    c = config
    speed = integral = derivative = previous = 0.0
    rows = []
    count = math.floor(c.duration / c.dt)
    for i in range(count + 1):
        time = i * c.dt
        error = c.target - speed
        # Derivative on measurement avoids a kick when the target changes.
        raw_d = -(speed - previous) / c.dt if i else 0.0
        derivative += c.dt / (0.05 + c.dt) * (raw_d - derivative)
        previous = speed
        candidate = integral + error * c.dt
        raw = c.kp * error + c.ki * candidate + c.kd * derivative
        command = max(-c.limit, min(c.limit, raw))
        # Conditional integration: freeze only when error pushes further into saturation.
        if raw == command or (raw - command) * error < 0:
            integral = candidate
        else:
            raw = c.kp * error + c.ki * integral + c.kd * derivative
            command = max(-c.limit, min(c.limit, raw))
        load = c.load if time >= c.load_at else 0.0
        rows.append((time, c.target, speed, command, load))
        # Exact update of a first-order plant under constant input during this interval.
        equilibrium = command - load
        speed = equilibrium + (speed - equilibrium) * math.exp(-c.dt / c.tau)
        if not all(math.isfinite(x) for x in (speed, integral, derivative)):
            raise ValueError('Numeric overflow: reduce gains or parameter magnitudes')
    return rows


def metrics(rows):
    dt = rows[1][0] - rows[0][0] if len(rows) > 1 else 0
    return {
        'final_error': rows[-1][1] - rows[-1][2],
        'peak_speed': max(r[2] for r in rows),
        'integral_absolute_error': sum(abs(r[1] - r[2]) for r in rows[:-1]) * dt,
    }


def gui():
    import tkinter as tk
    from tkinter import messagebox, ttk
    root = tk.Tk()
    root.title('PID Playground · Engineering Lab')
    root.geometry('950x650')
    panel = ttk.Frame(root, padding=16)
    panel.pack(fill='both', expand=True)
    ttk.Label(panel, text='Tune a speed controller', font=('', 20, 'bold')).pack(anchor='w')
    ttk.Label(panel, text='First-order plant · load disturbance at 6 s · command limited to ±3').pack(anchor='w')
    controls = ttk.Frame(panel)
    controls.pack(fill='x', pady=12)
    values = {}
    for name, default in [('kp', 2), ('ki', 1), ('kd', 0.1)]:
        ttk.Label(controls, text=name.upper()).pack(side='left', padx=5)
        value = tk.StringVar(value=str(default))
        ttk.Entry(controls, textvariable=value, width=8).pack(side='left')
        values[name] = value
    canvas = tk.Canvas(panel, background='#101827', highlightthickness=0)
    canvas.pack(fill='both', expand=True)
    status = tk.StringVar()
    ttk.Label(panel, textvariable=status).pack(anchor='w', pady=8)

    def redraw(event=None):
        try:
            rows = simulate(Config(**{k: float(v.get()) for k, v in values.items()}))
        except ValueError as exc:
            messagebox.showerror('Invalid settings', str(exc))
            return
        canvas.delete('all')
        width, height = max(canvas.winfo_width(), 300), max(canvas.winfo_height(), 200)
        left, top, right, bottom = 65, 40, width - 20, height - 40
        low = min(0, min(r[2] for r in rows))
        high = max(1.2, max(r[2] for r in rows))
        span = high - low
        for i in range(6):
            y = top + (bottom - top) * i / 5
            canvas.create_line(left, y, right, y, fill='#26344a')
            canvas.create_text(left - 8, y, text=f'{high-span*i/5:.2f}', anchor='e', fill='#b9c6d9')
        def point(t, y):
            return left + t / rows[-1][0] * (right-left), bottom - (y-low)/span*(bottom-top)
        for column, color in [(1, '#f6c85f'), (2, '#54d6bd')]:
            points = [coordinate for row in rows for coordinate in point(row[0], row[column])]
            canvas.create_line(*points, fill=color, width=2)
        x, _ = point(6, 0)
        canvas.create_line(x, top, x, bottom, fill='#ed8297', dash=(4, 4))
        canvas.create_text(left, 18, anchor='w', text='TARGET (yellow)    SPEED (green)    LOAD STEP (pink)', fill='#e1e9f5')
        canvas.create_text((left+right)/2, height-15, text='Time (seconds): 0 → 12', fill='#b9c6d9')
        m = metrics(rows)
        status.set('   '.join(f'{k.replace("_", " ")}: {v:.4f}' for k, v in m.items()))

    ttk.Button(controls, text='Simulate', command=redraw).pack(side='left', padx=12)
    canvas.bind('<Configure>', redraw)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui', action='store_true', help='Launch interactive gain controls')
    for name, value in vars(Config()).items():
        parser.add_argument('--' + name.replace('_', '-'), type=float, default=value)
    parser.add_argument('--output', type=Path, default=Path('response.csv'))
    args = parser.parse_args()
    if args.gui:
        gui()
        return
    try:
        rows = simulate(Config(**{k: getattr(args, k) for k in vars(Config())}))
        with args.output.open('w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['time_s', 'target', 'speed', 'command', 'load'])
            writer.writerows(rows)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    for name, value in metrics(rows).items():
        print(f'{name}={value:.6f}')
    print(f'Wrote {len(rows)} samples to {args.output}')


if __name__ == '__main__':
    main()

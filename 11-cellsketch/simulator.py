"""Deterministic workcell simulation: FIFO queues, parallel servers and travel."""
import copy
import hashlib
import heapq
import json
import math
from collections import deque


def example():
    return {'schema_version':1, 'jobs':40, 'arrival_interval_s':3., 'horizon_s':180., 'travel_speed_m_s':1.,
            'stations':[{'id':'load','name':'Loading table','kind':'workbench','x':5.,'y':8.,'cycle_s':2.,'capacity':1},
                        {'id':'robot','name':'Robot assembly','kind':'robot','x':15.,'y':8.,'cycle_s':5.,'capacity':1},
                        {'id':'exit','name':'Exit conveyor','kind':'conveyor','x':25.,'y':14.,'cycle_s':2.,'capacity':1}]}


def validate(model):
    if not isinstance(model,dict) or model.get('schema_version')!=1:
        raise ValueError('Expected workcell schema_version 1')
    if type(model.get('jobs')) is not int or not 1<=model['jobs']<=2000:
        raise ValueError('Jobs must be an integer between 1 and 2000')
    def numeric(value,name,low,high):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError(f'{name} must be finite and between {low} and {high}')
    numeric(model.get('arrival_interval_s'),'Arrival interval',0,100000)
    numeric(model.get('horizon_s'),'Horizon',0.001,1000000)
    numeric(model.get('travel_speed_m_s'),'Travel speed',0.001,1000)
    stations=model.get('stations')
    if not isinstance(stations,list) or not 1<=len(stations)<=20:
        raise ValueError('Provide 1..20 process stations in route order')
    ids=set()
    for station in stations:
        if not isinstance(station,dict):raise ValueError('Station must be an object')
        key=station.get('id')
        if not isinstance(key,str) or not 1<=len(key)<=80 or key in ids:raise ValueError('Station IDs must be unique nonempty strings')
        ids.add(key)
        if not isinstance(station.get('name'),str) or not 1<=len(station['name'])<=80:raise ValueError('Station name required (1..80 characters)')
        if station.get('kind') not in {'robot','workbench','conveyor'}:raise ValueError('Unknown equipment kind')
        numeric(station.get('x'),'X metres',0,40);numeric(station.get('y'),'Y metres',0,25)
        numeric(station.get('cycle_s'),'Cycle time',0.001,100000)
        if type(station.get('capacity')) is not int or not 1<=station['capacity']<=20:raise ValueError('Station capacity must be 1..20')
    return model


def simulate(model):
    validate(model)
    model=copy.deepcopy(model)
    stations=model['stations'];horizon=model['horizon_s'];events=[];sequence=0;trace=[]
    states=[{'queue':deque(),'busy':0,'last':0.,'queue_area':0.,'busy_area':0.,'started':0,'finished':0,'wait_sum':0.} for _ in stations]
    arrivals={};done={}
    def schedule(time,kind,index,job):
        nonlocal sequence
        # Service completions precede arrivals at exactly the same time.
        heapq.heappush(events,(time,0 if kind=='finish' else 1,sequence,kind,index,job));sequence+=1
    def touch(index,time):
        s=states[index];elapsed=time-s['last']
        s['queue_area']+=elapsed*len(s['queue']);s['busy_area']+=elapsed*s['busy'];s['last']=time
    def record(time,kind,index,job):
        s=states[index]
        trace.append({'time_s':time,'event':kind,'station':stations[index]['id'],'job':job,'queue':len(s['queue']),'busy':s['busy']})
    def dispatch(index,time):
        s=states[index];station=stations[index]
        while s['queue'] and s['busy']<station['capacity']:
            job,entered=s['queue'].popleft();s['busy']+=1;s['started']+=1;s['wait_sum']+=time-entered
            record(time,'service_start',index,job)
            schedule(time+station['cycle_s'],'finish',index,job)
    for job in range(model['jobs']):
        time=job*model['arrival_interval_s']
        if time<=horizon:schedule(time,'arrival',0,job)
    while events and events[0][0]<=horizon:
        time,_,_,kind,index,job=heapq.heappop(events);s=states[index];touch(index,time)
        if kind=='arrival':
            if index==0:arrivals[job]=time
            s['queue'].append((job,time));record(time,'queue_enter',index,job);dispatch(index,time)
        else:
            s['busy']-=1;s['finished']+=1;record(time,'service_finish',index,job)
            if index==len(stations)-1:
                done[job]=time;record(time,'job_complete',index,job)
            else:
                a,b=stations[index:index+2]
                distance=math.hypot(a['x']-b['x'],a['y']-b['y'])
                schedule(time+distance/model['travel_speed_m_s'],'arrival',index+1,job)
            dispatch(index,time)
    station_reports=[]
    for i,(station,s) in enumerate(zip(stations,states)):
        touch(i,horizon)
        station_reports.append({'id':station['id'],'name':station['name'],
            'utilization':s['busy_area']/(horizon*station['capacity']),
            'average_queue':s['queue_area']/horizon,'queue_at_end':len(s['queue']),'busy_at_end':s['busy'],
            'mean_wait_s_started_jobs':s['wait_sum']/s['started'] if s['started'] else None,
            'started':s['started'],'finished':s['finished']})
    bottleneck=max(station_reports,key=lambda s:s['utilization'])['id']
    summary={'arrived_jobs':len(arrivals),'completed_jobs':len(done),'wip_at_end':len(arrivals)-len(done),
             'throughput_jobs_per_hour':len(done)/horizon*3600,
             'mean_lead_time_s_completed_jobs':sum(t-arrivals[j] for j,t in done.items())/len(done) if done else None,
             'last_completion_s':max(done.values()) if done else None,
             'highest_utilization_station':bottleneck}
    digest=hashlib.sha256(json.dumps(model,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return {'schema_version':1,'model_sha256':digest,'model':model,'summary':summary,'stations':station_reports,'events':trace}

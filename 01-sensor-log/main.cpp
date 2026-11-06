#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

// Streaming Welford statistics: constant memory, stable variance.
struct Stats {
    size_t n = 0;
    double mean = 0, m2 = 0, low = 0, high = 0;
    void add(double x) {
        if (n == 0) low = high = x;
        low = std::min(low, x); high = std::max(high, x);
        ++n;
        double delta = x - mean;
        mean += delta / n;
        m2 += delta * (x - mean);
    }
};

bool number(const std::string& text, double& result) {
    std::istringstream stream(text);
    stream >> result;
    if (!stream || !std::isfinite(result)) return false;
    stream >> std::ws;
    return stream.eof();
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: sensor-log samples.csv\nExpected header: timestamp,value\n";
        return 2;
    }
    std::ifstream input(argv[1]);
    if (!input) { std::cerr << "Cannot open input file\n"; return 2; }
    std::string line;
    if (!std::getline(input, line)) { std::cerr << "Empty input\n"; return 2; }
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line != "timestamp,value") { std::cerr << "Invalid CSV header\n"; return 2; }
    Stats stats;
    size_t rejected = 0, row = 1;
    double previous = 0;
    bool have_previous = false;
    while (std::getline(input, line)) {
        ++row;
        const auto comma = line.find(',');
        double timestamp, value;
        if (comma == std::string::npos || line.find(',', comma + 1) != std::string::npos ||
            !number(line.substr(0, comma), timestamp) ||
            !number(line.substr(comma + 1), value) || timestamp < 0 ||
            (have_previous && timestamp <= previous)) {
            std::cerr << "Rejected row " << row << ": invalid sample or timestamp\n";
            ++rejected; continue;
        }
        stats.add(value); previous = timestamp; have_previous = true;
    }
    if (input.bad()) { std::cerr << "Input read failed\n"; return 2; }
    if (!stats.n) { std::cerr << "No valid samples\n"; return 1; }
    std::cout << std::fixed << std::setprecision(4)
              << "accepted=" << stats.n << " rejected=" << rejected
              << "\nmin=" << stats.low << " max=" << stats.high
              << " mean=" << stats.mean
              << "\npopulation_stddev=" << std::sqrt(stats.m2 / stats.n) << '\n';
    return rejected ? 1 : 0;
}

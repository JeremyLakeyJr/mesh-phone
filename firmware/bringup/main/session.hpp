#pragma once
#include <array>
#include <cstdint>
#include <string_view>
#include "keypad/controller.hpp"
namespace bringup {
enum class Command { start, stop, status, invalid };
class LineParser {
    std::array<char, 32> line_{};
    unsigned size_ = 0;
    bool overflow_ = false;
public:
    bool feed(char c, Command &command) {
        if (c != '\n') {
            if (size_ == line_.size()) overflow_ = true;
            else line_[size_++] = c;
            return false;
        }
        if (size_ && line_[size_-1] == '\r') --size_;
        const std::string_view text(line_.data(), size_);
        command = !overflow_ && text == "start" ? Command::start :
                  !overflow_ && text == "stop" ? Command::stop :
                  !overflow_ && text == "status" ? Command::status : Command::invalid;
        size_ = 0; overflow_ = false;
        return true;
    }
};
template<class Scanner> class Session {
    Scanner &scanner_;
    bool active_ = false, valid_ = false;
    std::uint16_t held_ = 0;
    keypad::Status fault_ = keypad::Status::reset_required;
public:
    explicit Session(Scanner &scanner) : scanner_(scanner) {}
    bool active() const { return active_; }
    bool valid() const { return valid_; }
    std::uint16_t held() const { return held_; }
    keypad::Status fault() const { return fault_; }
    bool start() {
        if (active_) return false; // Never flush a live session on repeated start.
        valid_ = false; held_ = 0;
        active_ = scanner_.initialize(); valid_ = active_; fault_ = scanner_.status();
        return active_;
    }
    void stop() { active_ = valid_ = false; held_ = 0; }
    keypad::Batch poll() {
        if (!active_) return {};
        auto batch = scanner_.poll();
        if (batch.status != keypad::Status::ready) {
            fault_ = batch.status; stop(); return batch;
        }
        for (unsigned i=0; i<batch.count; ++i) {
            const auto &event = batch.events[i];
            const auto bit = static_cast<std::uint16_t>(1u << (event.row*4+event.column));
            if (event.pressed) held_ |= bit; else held_ &= static_cast<std::uint16_t>(~bit);
        }
        return batch;
    }
};
}

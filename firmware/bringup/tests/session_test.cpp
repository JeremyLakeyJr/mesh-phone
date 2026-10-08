#include "../main/session.hpp"
#include <cassert>
#include <iostream>
#include <string>
struct FakeScanner {
    unsigned init_calls=0, polls=0;
    bool succeeds=true;
    keypad::Batch batch{};
    bool initialize() { ++init_calls; return succeeds; }
    keypad::Status status() const { return succeeds?keypad::Status::ready:keypad::Status::bus_error; }
    keypad::Batch poll() { ++polls; return batch; }
};
int main() {
    unsigned tests=0;
    FakeScanner scanner;
    bringup::Session<FakeScanner> session(scanner);
    assert(!session.active() && !session.valid()); session.poll(); assert(scanner.polls==0); ++tests;
    assert(session.start() && session.valid()); assert(!session.start() && scanner.init_calls==1); ++tests;
    scanner.batch.status=keypad::Status::ready; scanner.batch.count=1;
    for(unsigned row=0;row<4;++row) for(unsigned col=0;col<4;++col) {
        scanner.batch.events[0]={static_cast<std::uint8_t>(row),static_cast<std::uint8_t>(col),true};
        session.poll(); assert(session.held() & (1u << (row*4+col)));
    }
    assert(session.held()==0xffff); ++tests;
    for(unsigned row=0;row<4;++row) for(unsigned col=0;col<4;++col) {
        scanner.batch.events[0]={static_cast<std::uint8_t>(row),static_cast<std::uint8_t>(col),false};
        session.poll(); assert(!(session.held() & (1u << (row*4+col))));
    }
    assert(session.held()==0); ++tests;
    scanner.batch.events[0]={3,3,true}; session.poll();
    scanner.batch.status=keypad::Status::overflow; session.poll();
    assert(!session.active() && !session.valid() && session.held()==0);
    const auto polls=scanner.polls; session.poll(); assert(scanner.polls==polls); ++tests;
    assert(session.start() && session.valid() && session.held()==0); ++tests;
    session.stop(); assert(!session.valid()); const auto before=scanner.polls; session.poll(); assert(scanner.polls==before); ++tests;
    scanner.succeeds=false; assert(!session.start() && !session.valid() && session.fault()==keypad::Status::bus_error); ++tests;
    bringup::LineParser parser; bringup::Command result=bringup::Command::invalid;
    for(char c:std::string("start")) assert(!parser.feed(c,result));
    assert(parser.feed('\n',result) && result==bringup::Command::start); ++tests;
    for(char c:std::string("stop\r")) assert(!parser.feed(c,result));
    assert(parser.feed('\n',result) && result==bringup::Command::stop); ++tests;
    for(char c:std::string(100,'x')+"start") assert(!parser.feed(c,result));
    assert(parser.feed('\n',result) && result==bringup::Command::invalid);
    for(char c:std::string("status")) assert(!parser.feed(c,result));
    assert(parser.feed('\n',result) && result==bringup::Command::status); ++tests;
    for(char c:std::string("sta\0rt",6)) assert(!parser.feed(c,result));
    assert(parser.feed('\n',result) && result==bringup::Command::invalid); ++tests;
    std::cout << tests << " bring-up session scenarios passed\n";
}

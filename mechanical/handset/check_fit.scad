// Empty intersection is expected for each test. Values match handset.scad.
use <handset.scad>
check="halves";
module battery_test() {translate([0,-39,2.801]) linear_extrude(12) square([38,67],center=true);}
module display_test() {translate([0,42.5,20.101]) linear_extrude(3.498) square([60.5,43.5],center=true);}
module board_test() {
 translate([0,0,17.201]) difference() {
  slab(66,142,1.598,1.5);
  translate([0,8,-1]) rr(27,24,4,1);
  for(x=[-30.5,30.5],y=[-68,68]) translate([x,y,-1]) cylinder(d=2.3,h=4,$fn=48);
 }
}
if(check=="halves") intersection() {rear();translate([0,0,26]) mirror([0,0,1]) front();}
if(check=="battery") intersection() {rear();battery_test();}
if(check=="display") intersection() {translate([0,0,26]) mirror([0,0,1]) front();display_test();}
if(check=="board") intersection() {union(){rear();translate([0,0,26]) mirror([0,0,1]) front();} board_test();}
if(check=="keycaps") intersection() {
 translate([0,0,26]) mirror([0,0,1]) front();
 union() {for(y=[-11,-26,-41,-56],x=[-22.5,-7.5,7.5,22.5]) translate([x,y,25.9]) mirror([0,0,1]) keycap();}
}
if(check=="cover") intersection() {rear();translate([0,40,0]) port_cover();}
// 1 micron offset excludes coincident seating surfaces from CGAL intersection.
if(check=="pod") intersection() {rear();translate([0,40,1.199-18]) module_pod();}

// Documented legacy LTE carrier envelope plus 0.5 mm foam above the pod floor.
if(check=="modem") intersection() {
 module_pod();
 translate([0,0,2.7]) linear_extrude(12.44) square([44.45,31.75],center=true);
}

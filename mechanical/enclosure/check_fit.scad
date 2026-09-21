// Subtract 0.001 mm from pod seating depth to exclude coplanar CGAL artifacts.
use <enclosure.scad>
check="halves";
if(check=="halves") intersection() {
 rear();
 translate([0,0,38.8]) mirror([0,0,1]) front();
}
if(check=="cover") intersection() {
 rear();
 translate([-3,-10,0]) port_cover();
}
if(check=="pod") intersection() {
 rear();
 translate([-3,-10,1.199-18]) module_pod();
}
if(check=="battery") intersection() {
 rear();
 translate([0,-51,3.201]) linear_extrude(12) square([67,38],center=true);
}

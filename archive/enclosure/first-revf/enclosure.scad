// Rev F prototype. Dimensions in mm; +Y is the top of the phone.
include <pcb_geometry.scad>
part = "layout"; // [layout,rear,front,assembly]
$fn = 48;
wall = 2.4;
floor_t = 2.4;
fit = 0.6;
pcb_t = 1.6;
// Rear clearance includes battery envelope and rear-mounted components.
pcb_z = 20;
front_clearance = 15;
seam_z = pcb_z + pcb_t + front_clearance;
face_t = 2.4;
iw = pcb_w + 2*fit;
ih = pcb_h + 2*fit;
ow = iw + 2*wall;
oh = ih + 2*wall;
// Small internal radius preserves clearance at square PCB corners.
inner_r = 1;
outer_r = inner_r + wall;
// Panel datums are provisional: connector position is not panel position.
display_center = [0, 33];
display_window = [50, 76];
trackball_center = [-4.5, -23];
trackball_d = 11;
// Battery uses removable foam/strap retention, away from expansion opening.
battery_center = [0, 43];
battery_envelope = [38, 54, 12];
module_window = [23, 14];
module_fasteners = [[-20,-10],[14,-10]];
closure = [[-ow/2-2,55],[ow/2+2,55],[-ow/2-2,-55],[ow/2+2,-55]];
module rounded(w,h,z,r) {
    linear_extrude(z) offset(r=r) square([w-2*r,h-2*r],center=true);
}
module rear() {
 difference() {
  union() {
   difference() {
    rounded(ow,oh,seam_z,outer_r);
    translate([0,0,floor_t]) rounded(iw,ih,seam_z,inner_r);
   }
   // Bosses start at the floor, aligned to actual H1-H4 centers.
   for(p=mounts) translate([p[0],p[1],floor_t-0.1]) cylinder(d=5.6,h=pcb_z-floor_t+0.1);
   for(p=closure) translate([p[0],p[1],0]) cylinder(d=7,h=seam_z);
  }
  for(p=mounts) translate([p[0],p[1],pcb_z-8]) cylinder(d=1.7,h=9);
  for(p=closure) translate([p[0],p[1],seam_z-10]) cylinder(d=1.7,h=11);
  // USB1 faces the right edge, not the bottom edge.
  translate([ow/2,usb[1],pcb_z+2]) cube([wall*4,12,7],center=true);
  translate([ow/2,power[1],pcb_z+3]) cube([wall*4,9,6],center=true);
  translate([expansion[0],expansion[1],-1]) linear_extrude(floor_t+2)
   offset(r=1) square([module_window[0]-2,module_window[1]-2],center=true);
  for(p=module_fasteners) translate([p[0],p[1],-1]) cylinder(d=2.3,h=floor_t+2);
 }
}
// Face down on the print bed; inside features grow upwards.
module front() {
 difference() {
  union() {
   rounded(ow,oh,face_t,outer_r);
   for(p=closure) translate([p[0],p[1],0]) cylinder(d=7,h=face_t);
   // Interrupted locating lip leaves corner PCB bosses and side ports clear.
   for(x=[-1,1]) translate([x*(iw/2-0.9),0,face_t]) cube([1.2,70,2],center=true);
  }
  translate([display_center[0],display_center[1],-1]) linear_extrude(face_t+2)
   offset(r=1) square(display_window-[2,2],center=true);
  translate([trackball_center[0],trackball_center[1],-1]) cylinder(d=trackball_d,h=face_t+2);
  for(p=keys) translate([p[0],p[1],-1]) cylinder(d=4.6,h=face_t+2);
  for(p=closure) translate([p[0],p[1],-1]) cylinder(d=2.3,h=face_t+2);
 }
}
assert(pcb_z-floor_t >= battery_envelope[2]+4, "Insufficient rear allowance");
assert(display_center[1]+display_window[1]/2 < ih/2-2, "Display overlaps rim");
if(part=="rear") rear();
else if(part=="front") front();
else if(part=="assembly") {
 color("SlateGray") rear();
 color("LightGray") translate([0,0,seam_z+face_t]) mirror([0,0,1]) front();
} else if(part=="layout") {
 translate([-ow/2-7,0,0]) rear();
 translate([ow/2+7,0,0]) front();
} else assert(false,"Unknown part");

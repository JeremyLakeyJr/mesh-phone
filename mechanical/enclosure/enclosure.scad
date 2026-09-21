// Pocket Rev F: millimetres, +Y towards phone top, rear exterior at Z=0.
include <pcb_geometry.scad>
part = "layout"; // [layout,rear,front,port_cover,module_pod,assembly,with_module,fit]
$fn=48;
wall=2.4; floor_t=2.4; face_t=2.4; fit=0.6; pcb_t=1.6;
// MakerFocus 3000 mAh: 65x36x10 nominal, +2 mm manufacturer tolerance.
battery=[67,38,12]; battery_center=[0,-51];
tray_floor=0.8; rear_component_gap=2.1;
pcb_z=floor_t+tray_floor+battery[2]+rear_component_gap;
// Reserve LTE carrier + provisional display thickness + assembly clearance.
lte_height=12.44; display_thickness=4; stack_clearance=1.06;
front_clearance=lte_height+display_thickness+stack_clearance;
seam_z=pcb_z+pcb_t+front_clearance;
height=seam_z+face_t;
iw=pcb_w+2*fit; ih=pcb_h+2*fit;
ow=iw+2*wall; oh=ih+2*wall;
inner_r=1; outer_r=3.4; bevel=1.0;
display_center=[0,30]; display_window=[50,76];
display_outline=[61,92.44]; // documented panel envelope; measure thickness
trackball_center=[-4.5,-23]; trackball_d=11;
port=[24,14]; dock=[68,44]; dock_recess=1.2; dock_fit=0.3;
module_depth=18; module_wall=2.4;
// Asymmetric third locator prevents rotating the cover/pod 180 degrees.
dock_screws=[[-29,0],[29,0]];
module_origin=expansion;
module profile(w,h,r) { offset(r=r) square([w-2*r,h-2*r],center=true); }
module rounded(w,h,z,r=3) { linear_extrude(z) profile(w,h,r); }
module body(z) {
 // Bevel exposed bed-side perimeter; wall remains full thickness at PCB plane.
 hull() {
  rounded(ow-2*bevel,oh-2*bevel,0.01,outer_r-bevel);
  translate([0,0,bevel]) rounded(ow,oh,0.01,outer_r);
 }
 translate([0,0,bevel]) rounded(ow,oh,z-bevel,outer_r);
}
module dock_at() { translate([module_origin[0],module_origin[1],0]) children(); }
module rear() {
 difference() {
  union() {
   difference() {
    body(seam_z);
    translate([0,0,floor_t]) rounded(iw,ih,seam_z,inner_r);
   }
   for(p=mounts) translate([p[0],p[1],floor_t-0.1]) cylinder(d=5.6,h=pcb_z-floor_t+0.1);
   // Low, rounded battery cradle: no hard lid pressing on the pouch.
   translate([battery_center[0],battery_center[1],floor_t-0.05]) {
    rounded(battery[0]+5,battery[1]+5,tray_floor+0.05,3);
    difference() {
     rounded(battery[0]+5,battery[1]+5,3.2,3);
     translate([0,0,tray_floor]) rounded(battery[0]+1.6,battery[1]+1.6,4,2);
     // Lead exit at top, well clear of the J16 opening.
     translate([0,battery[1]/2,3]) cube([14,10,6],center=true);
    }
   }
   // Strap bridges beside cradle; transverse slots are cut below.
   for(x=[-1,1]) translate([battery_center[0]+x*(battery[0]/2+5),battery_center[1],floor_t-0.1])
    rounded(6,13,4.1,1.2);
   dock_at() for(p=dock_screws) translate([p[0],p[1],floor_t-0.1]) cylinder(d=7.5,h=4.5);
  }
  for(p=mounts) translate([p[0],p[1],pcb_z-9]) cylinder(d=1.7,h=10);
  // Recessed plug approach and actuator access, radiused to reduce stress risers.
  translate([ow/2+1,usb[1],pcb_z+2]) rotate([0,-90,0])
   linear_extrude(wall*3) profile(7,12,1.5);
  translate([ow/2+1,power[1],pcb_z+3]) rotate([0,-90,0])
   linear_extrude(wall*3) profile(6,9,1.2);
  dock_at() {
   translate([0,0,-0.01]) rounded(dock[0]+2*dock_fit,dock[1]+2*dock_fit,dock_recess+0.01,3);
   translate([0,0,-1]) rounded(port[0],port[1],floor_t+2,2);
   for(p=dock_screws) {
    translate([p[0],p[1],-1]) cylinder(d=2.3,h=9);
    // Captive M2 hex nut, inserted from inside before PCB installation.
    translate([p[0],p[1],4.3]) cylinder(d=4.8,h=4,$fn=6);
   }
   translate([-23,15,-0.1]) cylinder(d=2.5,h=2.5);
  }
  for(x=[-1,1]) translate([battery_center[0]+x*(battery[0]/2+5),battery_center[1],floor_t+1.5])
   cube([9,9,1.8],center=true);
 }
}
// Print outer face on bed. Mirror only Z for assembly; retain all XY datums.
module front() {
 difference() {
  union() {
   body(face_t);
   for(p=mounts) translate([p[0],p[1],face_t-0.1]) cylinder(d=5.6,h=front_clearance+0.1);
   // Perimeter tongue seats below seam, above all PCB edges.
   translate([0,0,face_t-0.1]) difference() {
    rounded(iw-0.5,ih-0.5,1.7,1.2);
    translate([0,0,-0.1]) rounded(iw-3.3,ih-3.3,2,1);
   }
   // Four panel location tabs; foam tape retains measured display on the ledge.
   for(x=[-1,1],y=[-1,1])
    translate([display_center[0]+x*(display_outline[0]/2+1),display_center[1]+y*32,face_t-0.1])
     rounded(1.6,9,2.5,0.5);
  }
  translate([display_center[0],display_center[1],-1]) rounded(display_window[0],display_window[1],face_t+2,2);
  translate([trackball_center[0],trackball_center[1],-1]) cylinder(d=trackball_d,h=face_t+2);
  for(p=keys) translate([p[0],p[1],-1]) cylinder(d=4.6,h=face_t+2);
  for(p=mounts) {
   translate([p[0],p[1],-1]) cylinder(d=2.3,h=front_clearance+face_t+2);
   translate([p[0],p[1],-0.01]) cylinder(d=4.2,h=1.1);
  }
 }
}
// Cover prints exterior-down, and sits flush in the rear pocket.
module port_cover() {
 difference() {
  union() {
   rounded(dock[0],dock[1],dock_recess,3);
   // Locator pin and shallow port plug support thin flush face.
   translate([-23,15,dock_recess-0.1]) cylinder(d=1.9,h=1.1);
   rounded(port[0]-0.6,port[1]-0.6,2.2,1.7);
  }
  for(p=dock_screws) translate([p[0],p[1],-1]) cylinder(d=2.3,h=4);
 }
}
// External pod: open side faces host, opening protected by host rear wall.
// Envelope 68x44x18; cable plugs into J16 before screwing pod to host.
module module_pod() {
 difference() {
  union() {
   difference() {
    rounded(dock[0],dock[1],module_depth,3);
    translate([0,0,module_wall]) rounded(dock[0]-2*module_wall,dock[1]-2*module_wall,module_depth,1);
   }
   for(p=dock_screws) translate([p[0],p[1],0]) cylinder(d=7.5,h=module_depth);
   translate([-23,15,module_wall-0.1]) cylinder(d=4,h=module_depth-module_wall+0.1);
   translate([-23,15,module_depth-0.1]) cylinder(d=1.9,h=1.1);
   // Strap anchors for removable module retention, no fixed module hole pattern.
   for(y=[-1,1]) translate([0,y*16,module_wall-0.1]) rounded(14,5,4.1,1);
  }
  for(p=dock_screws) {
   translate([p[0],p[1],-1]) cylinder(d=2.3,h=module_depth+2);
   translate([p[0],p[1],-0.1]) cylinder(d=4.5,h=1.3);
  }
  for(y=[-1,1]) translate([0,y*16,module_wall+1.7]) cube([10,8,1.8],center=true);
 }
}
module assembly(with_pod=false) {
 color("#314753") rear();
 color("#62838a") translate([0,0,height]) mirror([0,0,1]) front();
 dock_at() color("#de9c46")
  if(with_pod) translate([0,0,dock_recess-module_depth]) module_pod();
  else port_cover();
}
module fit_view() {
 assembly();
 %translate([0,0,pcb_z]) linear_extrude(pcb_t) square([pcb_w,pcb_h],center=true);
 %translate([battery_center[0],battery_center[1],floor_t+tray_floor]) rounded(battery[0],battery[1],battery[2],2);
 %translate([display_center[0],display_center[1],seam_z-display_thickness]) rounded(display_outline[0],display_outline[1],display_thickness,1);
}
assert(pcb_z-floor_t-tray_floor-battery[2]>=rear_component_gap-0.001);
assert(battery_center[1]+battery[1]/2+2.5 < expansion[1]-port[1]/2-1,"Battery overlaps port");
assert(display_center[1]+display_outline[1]/2 < ih/2-0.5,"Panel hits rim");
echo(body_mm=[ow,oh,height], module_added_depth=module_depth-dock_recess);
if(part=="rear") rear();
else if(part=="front") front();
else if(part=="port_cover") port_cover();
else if(part=="module_pod") module_pod();
else if(part=="assembly") assembly();
else if(part=="with_module") assembly(true);
else if(part=="fit") fit_view();
else if(part=="layout") {
 translate([-ow/2-5,0,0]) rear();
 translate([ow/2+5,0,0]) front();
 translate([-40,-oh/2-30,0]) port_cover();
 translate([40,-oh/2-30,0]) module_pod();
} else assert(false,"Unknown part");

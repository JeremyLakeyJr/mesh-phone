// MAKERphone-inspired industrial design. Requires a NEW PCB and smaller display.
// This source does not fit the existing 87x154 Rev F PCB.
part="layout"; // [rear,front,keycap,port_cover,module_pod,assembly,layout,fit]
$fn=48;
w=74; h=154; depth=26;
wall=2.4; floor_t=2.2; face_t=2.4; seam=depth-face_t;
corner=7; fit=0.3;
board=[66,138,1.6]; board_z=17.2;
battery=[38,67,12]; battery_center=[0,-39]; battery_z=2.8;
// Rotated ER-TFT024IPS-3 candidate. Envelope includes provisional CTP/Z margin.
screen_center=[0,42.5]; screen_window=[48.5,36.3]; screen_envelope=[60.5,43.5,3.5];
ball_center=[0,8]; ball_aperture=[27,24];
keys=[for(y=[-11,-26,-41,-56],x=[-22.5,-7.5,7.5,22.5]) [x,y]];
mounts=[[-30.5,68],[30.5,68],[-30.5,-68],[30.5,-68]];
dock_center=[0,40]; dock=[66,48]; dock_recess=1.2;
pod_depth=18;
// Straight clipped corners and broad bevels establish the reference silhouette.
module outline(ww,hh,c) {
 polygon([[-ww/2+c,-hh/2],[ww/2-c,-hh/2],[ww/2,-hh/2+c],
 [ww/2,hh/2-c],[ww/2-c,hh/2],[-ww/2+c,hh/2],[-ww/2,hh/2-c],[-ww/2,-hh/2+c]]);
}
module slab(ww,hh,zz,c=4) {linear_extrude(zz) outline(ww,hh,c);}
module rr(ww,hh,zz,r=1) {
 linear_extrude(zz) offset(r=r) square([ww-2*r,hh-2*r],center=true);
}
module skin(zz) {
 hull() {
  slab(w-3,h-3,0.02,corner-0.8);
  translate([0,0,1.5]) slab(w,h,0.02,corner);
 }
 translate([0,0,1.5]) slab(w,h,zz-1.5,corner);
}
module dock_at() {translate([dock_center[0],dock_center[1],0]) children();}
module rear() {
 difference() {
  union() {
   difference() {
    skin(seam);
    translate([0,0,floor_t]) slab(w-2*wall,h-2*wall,seam,corner-wall);
   }
   // Future-board mounting posts; holes differ from Rev F.
   for(p=mounts) translate([p[0],p[1],floor_t-0.1]) cylinder(d=6,h=board_z-floor_t+0.1);
   translate([battery_center[0],battery_center[1],floor_t-0.05]) {
    rr(battery[0]+4,battery[1]+4,0.65,2);
    difference() {
     rr(battery[0]+4,battery[1]+4,3.0,2);
     translate([0,0,0.6]) rr(battery[0]+1.4,battery[1]+1.4,4,1);
     translate([0,battery[1]/2,2]) cube([12,8,5],center=true);
    }
   }
   for(x=[-1,1]) translate([x*24,battery_center[1],floor_t-0.1]) rr(6,12,4.1,1);
   dock_at() for(x=[-29,29]) translate([x,0,floor_t-0.1]) cylinder(d=7,h=4.5);
  }
  for(p=mounts) translate([p[0],p[1],board_z-8]) cylinder(d=1.7,h=9);
  // Top-facing IR transmitter and receiver; measured carrier required.
  for(x=[-18,18]) translate([x,h/2+1,12]) rotate([90,0,0]) cylinder(d=6,h=7);
  // Proposed microSD access on the redesigned board.
  translate([w/2+1,0,board_z+1.5]) rotate([0,-90,0]) linear_extrude(6) offset(r=0.4) square([1.8,13],center=true);
  // Speaker vents: upper left side, separate from the display envelope.
  for(y=[56,59,62]) translate([-w/2-1,y,10]) rotate([0,90,0]) cylinder(d=1.5,h=7);
  // Side grip channels are shallow: minimum side wall 1.8 mm.
  for(x=[-1,1], y=[-49,-44,-39,-34,-29])
   translate([x*(w/2-0.15),y,9]) cube([0.9,1.1,8],center=true);
  // USB and power: proposed board locations, not Rev F locations.
  translate([w/2+1,44,board_z+1.8]) rotate([0,-90,0]) linear_extrude(6) offset(r=1) square([4.5,10],center=true);
  translate([-w/2-1,59,board_z+2.2]) rotate([0,90,0]) linear_extrude(6) offset(r=0.8) square([3,6],center=true);
  dock_at() {
   translate([0,0,-0.1]) slab(dock[0]+0.6,dock[1]+0.6,dock_recess+0.1,3);
   // Separate modem harness and independent J16 expansion paths.
   translate([0,8,-1]) rr(22,10,floor_t+2,1.5);
   translate([0,-12,-1]) rr(18,8,floor_t+2,1.2);
   for(x=[-29,29]) {
    translate([x,0,-1]) cylinder(d=2.3,h=9);
    translate([x,0,4.3]) cylinder(d=4.8,h=4,$fn=6);
   }
   translate([-24,19,-0.1]) cylinder(d=2.5,h=2.5);
  }
  for(x=[-24,24]) translate([x,battery_center[1],floor_t+1.5]) cube([8,8,1.8],center=true);
 }
}
module front() {
 difference() {
  union() {
   skin(face_t);
   for(p=mounts) translate([p[0],p[1],face_t-0.1]) cylinder(d=6,h=4.9);
   translate([0,0,face_t-0.1]) difference() {
    slab(w-2*wall-0.5,h-2*wall-0.5,1.6,corner-wall);
    translate([0,0,-0.1]) slab(w-2*wall-3.1,h-2*wall-3.1,2,corner-wall-1.3);
   }
   // Screen panel location ribs inside the upper frame.
   for(x=[-1,1]) translate([x*31.2,42.5,face_t-0.1]) rr(1.5,39,2,0.4);
  }
  translate([screen_center[0],screen_center[1],-1]) slab(screen_window[0],screen_window[1],face_t+2,1.5);
  // Recessed display lens surround and keypad deck retain a structural web.
  translate([0,42.5,-0.01]) slab(62,41,0.55,2.5);
  translate([0,-33.5,-0.01]) slab(63,62,0.4,3);
  translate([ball_center[0],ball_center[1],-1]) cylinder(d=11.2,h=face_t+2);
  translate([ball_center[0],ball_center[1],-0.01]) cylinder(d=16,h=0.5);
  for(p=keys) translate([p[0],p[1],-1]) rr(10.2,7.6,face_t+2,1);
  for(p=mounts) {
   translate([p[0],p[1],-1]) cylinder(d=2.3,h=9);
   translate([p[0],p[1],-0.01]) cylinder(d=4.2,h=1.1);
  }
  // Recessed earpiece styling; actual speaker vents are in the left side.
  for(y=[71.8,73.3]) translate([0,y,-0.01]) rr(18,0.8,0.45,0.3);
  translate([0,-71,-1]) cylinder(d=1.4,h=face_t+2);
  for(x=[-26,26]) translate([x,8,-0.01]) rr(7,2,0.45,0.6);
 }
}
// Face-down print. Retaining flange is installed from inside before closure.
module keycap() {
 hull() {
  rr(8.9,6.3,0.05,0.8);
  translate([0,0,0.55]) rr(9.6,7,0.05,1);
 }
 translate([0,0,0.55]) rr(9.6,7,1.85,1);
 translate([0,0,2.35]) rr(11.3,8.7,0.8,1);
 translate([0,0,3.1]) cylinder(d=3,h=1.2);
}
module port_cover() {
 difference() {
  union() {
   slab(dock[0],dock[1],dock_recess,3);
   translate([0,8,0]) rr(21.4,9.4,2,1.2);
   translate([0,-12,0]) rr(17.4,7.4,2,1);
   translate([-24,19,dock_recess-0.1]) cylinder(d=1.9,h=1.1);
  }
  for(x=[-29,29]) translate([x,0,-1]) cylinder(d=2.3,h=4);
 }
}
module module_pod() {
 difference() {
  union() {
   difference() {
    slab(dock[0],dock[1],pod_depth,3);
    translate([0,0,2.2]) slab(dock[0]-4.8,dock[1]-4.8,pod_depth,1.4);
   }
   for(x=[-29,29]) translate([x,0,0]) cylinder(d=7,h=pod_depth);
   translate([-24,19,2.1]) cylinder(d=4,h=pod_depth-2.1);
   translate([-24,19,pod_depth-0.1]) cylinder(d=1.9,h=1.1);
  }
  // SIM access on the selected modem carrier; final position must be measured.
  translate([dock[0]/2+1,0,10]) rotate([0,-90,0]) linear_extrude(7) offset(r=0.4) square([1.8,15],center=true);
  // Independent expansion cable exit remains usable with LTE pod attached.
  translate([-dock[0]/2-1,-12,8]) rotate([0,90,0]) linear_extrude(7) offset(r=1) square([4,9],center=true);
  for(x=[-29,29]) {
   translate([x,0,-1]) cylinder(d=2.3,h=pod_depth+2);
   translate([x,0,-0.01]) cylinder(d=4.2,h=1.1);
  }
 }
}
module assembly() {
 color("#252b2e") rear();
 color("#353c40") translate([0,0,depth]) mirror([0,0,1]) front();
 for(p=keys) color("#171b1e") translate([p[0],p[1],depth-0.1]) mirror([0,0,1]) keycap();
 dock_at() color("#33393d") port_cover();
}
module fit_view() {
 assembly();
 %translate([battery_center[0],battery_center[1],battery_z]) rr(battery[0],battery[1],battery[2],1);
 %translate([0,0,board_z]) difference() {
  slab(board[0],board[1],board[2],1.5);
  translate([ball_center[0],ball_center[1],-1]) rr(ball_aperture[0],ball_aperture[1],4,1);
 }
 %translate([0,42.5,seam-screen_envelope[2]]) slab(screen_envelope[0],screen_envelope[1],screen_envelope[2],1);
}
assert(battery_center[1]+battery[1]/2 < ball_center[1]-ball_aperture[1]/2-1);
assert(board_z-battery_z-battery[2]>=2.3);
echo(design="NEW PCB REQUIRED",body=[w,h,depth],battery=battery);
if(part=="rear") rear();
else if(part=="front") front();
else if(part=="keycap") keycap();
else if(part=="port_cover") port_cover();
else if(part=="module_pod") module_pod();
else if(part=="assembly") assembly();
else if(part=="fit") fit_view();
else if(part=="layout") {
 translate([-42,0,0]) rear(); translate([42,0,0]) front();
 translate([-37,-105,0]) port_cover(); translate([37,-105,0]) module_pod();
 translate([0,-140,0]) keycap();
} else assert(false,"Unknown part");

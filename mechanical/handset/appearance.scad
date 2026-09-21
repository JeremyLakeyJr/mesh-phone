// RENDER-ONLY props: display, labels, ball and screw heads. Not electrical parts.
part="display";
$fn=40;
module box(w,h,t) {linear_extrude(t) square([w,h],center=true);}
module label(t,p,size=2) {translate(p) linear_extrude(0.05) text(t,size=size,halign="center",valign="center",font="DejaVu Sans:style=Bold");}
if(part=="display") translate([0,42.5,24.7]) box(48.5,36.3,0.5);
if(part=="ball") translate([0,8,23.5]) sphere(r=4.8);
if(part=="ring") translate([0,8,25.5]) difference() {cylinder(d=15,h=0.45);translate([0,0,-0.1]) cylinder(d=11.2,h=1);}
if(part=="screws") for(x=[-30.5,30.5],y=[-68,68]) translate([x,y,25]) difference() {
 cylinder(d=3.8,h=0.8);translate([0,0,0.5]) cube([2.5,0.6,1],center=true);
}
if(part=="legends") {
 names=["1","2","3","A","4","5","6","B","7","8","9","C","*","0","#","D"];
 for(i=[0:15]) label(names[i],[-22.5+(i%4)*15,-11-floor(i/4)*15,25.92],2.4);
 label("MESH",[0,-66,26.01],1.8);
 label("915",[-25,8,26.01],1.5);label("GPS",[25,8,26.01],1.5);
}
if(part=="ui") {
 label("MESH / 4G",[0,57.5,25.22],1.9);
 label("12:42",[0,45.5,25.22],6);
 label("LORA    GPS    NFC",[0,31.5,25.22],1.65);
 label("CONNECTED",[0,26,25.22],1.2);
}

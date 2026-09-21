// ============================================================
//  OWASSO-1 rev A — Enclosure v2 (measurement-corrected)
//
//  PCB: 70 x 154mm actual Edge.Cuts
//  Stack (bottom→top):
//    floor 1.6 | battery 10 | air gap 1 | standoff 11 | PCB 1.6 |
//    tallest module ≈ 13 (2.54 header + A7670 board) | keycaps 3
//  Internal depth = 1.6+8+1+9+1.6+13+3 +0.5 clearance ≈ 37.7
//
//  Coordinate system: enclosure centered at origin, PCB origin
//  maps to (-pcb_w/2, -pcb_h/2) so KiCad (x,y) → enclosure
//  (x - pcb_w/2, y - pcb_h/2). All cutouts derive from PCB
//  footprint positions via pcb2case().
//
//  Print: PETG, 0.2mm layers, 3 walls, 15% infill. No supports.
// ============================================================

/* [PCB] */
pcb_w = 70;         // actual Edge.Cuts width
pcb_h = 154;        // actual Edge.Cuts height
pcb_t = 1.6;

/* [Heights above PCB top surface] */
h_header_a7670 = 2.54;   // J1 header pins
h_a7670_board = 10;      // core board incl. components + SIM tray side-clearance
h_keycap = 2;            // SKRP + cap
h_lcd = 4;               // 3.5in 320x480 panel w/ FPC folded

/* [Battery] */
// MakerFocus 3.7 V 2000 mAh flat LiPo nominal envelope is
// approximately 50 x 34 x 10 mm.  The cavity adds 2 mm total
// XY clearance and 2 mm thickness clearance for insulation/tolerance.
batt_l = 54;
batt_w = 38;
batt_t = 12;

/* [Case] */
wall = 2.0;
floor_t = 1.6;
clearance = 0.5;
corner_r = 6;
standoff_h = batt_t + 1;   // PCB must clear battery pouch: 13mm
air_gap = 1;               // between battery top and PCB bottom

stack_total = h_header_a7670 + h_a7670_board;   // tallest point on PCB top
case_inner_w = pcb_w + 2*clearance;
case_inner_h = pcb_h + 2*clearance;
case_inner_d = floor_t + batt_t + air_gap + standoff_h - floor_t + pcb_t + stack_total + h_keycap + clearance;
// = 1.6+12+1+(13-1.6)+1.6+12.54+2+0.5 ≈ 39.6

$fn = 64;

// PCB coord -> enclosure coord (KiCad origin at PCB corner)
function px(kx) = kx - pcb_w/2;
function py(ky) = ky - pcb_h/2;

module rbox(w, h, d, r) {
    hull() {
        for (sx=[-1,1], sy=[-1,1])
            translate([sx*(w/2-r), sy*(h/2-r), 0])
                cylinder(r=r, h=d);
    }
}

// ================= FRONT BEZEL =================
bezel_depth = 5;

difference() {
    translate([0, 0, -bezel_depth])
        rbox(case_inner_w + 2*wall, case_inner_h + 2*wall, bezel_depth + wall, corner_r);

    // hollow: through-opening for the component stack
    translate([0, 0, -bezel_depth])
        rbox(case_inner_w, case_inner_h, bezel_depth + wall + 2, corner_r - 1);

    // ---- LCD window: 3.5in panel, approx. 54.5 x 83 mm ----
    // Panel basis: 320x480 IPS FPC display, outline 54.5 x 83 mm.
    translate([px(35), py(43), 0])
        cube([56, 84, bezel_depth + 2*wall + 4], center=true);

    // ---- Trackball: front-panel module near the upper input area ----
    translate([px(8), py(68), 0])
        cylinder(d=11, h=bezel_depth + 2*wall + 4, center=true);

    // ---- Camera hole: J8 at KiCad(52,10), lens d=8 → hole 9 ----
        translate([px(52), py(10), 0])
        cylinder(d=9, h=bezel_depth + 2*wall + 4, center=true);

    // ---- Keypad 4x4: compact KMR2 switch centers match rebuild_pcb.py. ----
    for (kx=[14,28,42,56], ky=[93,105,117,129])
        translate([px(kx), py(ky), 0])
            cylinder(d=4, h=bezel_depth + 2*wall + 4, center=true);

    // ---- IR receiver window: U7 at KiCad(60,40) ----
    translate([px(60), py(40), 0])
        cylinder(d=6, h=bezel_depth + 2*wall + 4, center=true);

    // ---- POWER BUTTON (side): SW1 slide switch at KiCad(65,32) ----
    // SS12D00 actuator: ~3x2mm nub on right edge of PCB. Side slot cut
    // through bezel wall at that height. Slot 6x4mm for thumb access.
        translate([case_inner_w/2 + wall/2, py(32), -bezel_depth/2])
        cube([wall + 2, 6, 4], center=true);
}

// ================= CLEAR LENS =================
// Sits IN bezel recess: covers LCD+trackball+camera zone, 1mm acrylic
lens_t = 1.0;
translate([0, 0, 0])   // glued under bezel lip at z = -bezel_depth..-bezel_depth+lens_t
difference() {
    translate([0, py((8+12)/2 + 20), -bezel_depth + lens_t/2])
        cube([case_inner_w - 6, 60, lens_t], center=true);
}

// ================= REAR SHELL =================
translate([0, -(case_inner_h + 2*wall + 8), 0]) {
    total_depth = wall + case_inner_d;

    difference() {
        rbox(case_inner_w + 2*wall, case_inner_h + 2*wall, total_depth, corner_r);

        // main cavity down to floor
        translate([0, 0, wall])
            rbox(case_inner_w, case_inner_h, total_depth, corner_r - 1);

        // ---- USB-C: USB1 KiCad(66,50). Receptacle z spans PCB-bottom-2 to PCB-top+3.
        // PCB bottom sits at wall+batt_t+air_gap+standoff_h... compute:
        pcb_bottom_z = wall + floor_t + batt_t + air_gap;   // 13.2? no:
        // floor is solid up to wall+floor_t; battery bay recessed into that.
        // Simpler: cavity floor at z=wall+floor_t. Battery 12mm. gap 1. PCB bottom
        // rests on standoffs of height standoff_h measured from cavity floor:
        // pcb_z = wall + floor_t + standoff_h = 2+1.6+13 = 16.6
        // USB-C mid-shell z ≈ pcb_z ± 3:
        translate([px(66), -case_inner_h/2 - wall - 1, 16.6])
            cube([10.5, 8, 5], center=true);   // 10.5 wide, deep enough to pierce wall

        // ---- LTE carrier interface is at J1 KiCad(10,20), left/top region ----
        translate([-case_inner_w/2 - wall/2, py(20), 16.6])
            cube([wall + 2, 8, 5], center=true);

        // ---- LoRa carrier interface is at J3 KiCad(40,90) ----
        translate([-case_inner_w/2 - wall/2, py(90), 16.6])
            cube([wall + 2, 8, 5], center=true);

        // ---- POWER BUTTON side slot in SHELL too: SW1 KiCad(65,32) ----
        // Shell z-range for the switch actuator:
        //   PCB bottom z = wall+floor_t+standoff_h = 2+1.6+13 = 16.6
        //   switch body height above PCB ≈ 3.5 → slot centered ≈ 16.6+1.75
        translate([case_inner_w/2 + wall/2, py(32), 18.4])
            cube([wall + 2, 6, 5], center=true);

        // ---- SD card slot right side: J9 at KiCad(68,20) ----
        translate([case_inner_w/2 + wall/2, py(20), 14.0])
            cube([wall + 2, 16, 2.6], center=true);

        // ---- SIM access right side: J10 at KiCad(62,75) ----
        translate([case_inner_w/2 + wall/2, py(75), 14.0])
            cube([wall + 2, 14, 2.6], center=true);

        // ---- Battery bay: pouch UNDER pcb, sits on cavity floor ----
        // centered horizontally; from bottom edge upward
        translate([0, -case_inner_h/2 + clearance + batt_l/2,
                   wall + floor_t + batt_t/2])
            %cube([batt_w, batt_l, batt_t], center=true);

        // ---- JST-XH battery lead exit bottom edge, offset from USB-C ----
        translate([px(20), -case_inner_h/2 - wall/2, wall + floor_t + 1.5])
            cube([8, wall + 2, 3], center=true);

        // ---- Speaker/mic holes optional bottom-right grid ----
        for (i=[-2:2])
            translate([px(52) + i*3, -case_inner_h/2 + 6, wall + floor_t/2])
                cylinder(d=1.5, h=floor_t*2, center=true);
    }

    // ---- Standoffs: 4 corners, M2 bosses, height puts PCB above battery ----
    // Must match mounting holes added to PCB at KiCad(6,6),(70,6),(6,154),(70,154)
    for (kx=[6, 70], ky=[6, 154])
        translate([px(kx), py(ky), wall + floor_t])
            difference() {
                cylinder(d=6, h=standoff_h);
                translate([0, 0, standoff_h - 6])
                    cylinder(d=2.2, h=7);   // M2 self-tap pilot
            }

    // ---- Battery strap slots (2x silicone/velcro strap cross-over) ----
    for (sy=[-18, 18])
        difference() {
            translate([0, sy, wall + floor_t - 0.01])
                cube([batt_w + 6, 4, 1.2], center=true);
        }
}

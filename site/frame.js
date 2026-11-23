// One map frame for the table.
// Paper atlas: x grows east, y grows south (image rows, top is north).
// World: +x east, +y up, −z north. Camera on +z looks north, so east is screen-right.
// Check: paper (50, 0) → z < 0; paper (100, 50) → x > 0.
// Camera theta = 0 sits on +z. Flat forward is (0, 0, −1). forward × up = (1, 0, 0).

export const UP = { x: 0, y: 1, z: 0 };
export const IMG = { w: 2010, h: 1350, left: 54, top: 184, right: 1956, bottom: 1225 };
export const PLANE_W = 20;
export const PLANE_H = (PLANE_W * IMG.h) / IMG.w;
export const BOARD_W = 16;
export const BOARD_H = 10;

export function paperToWorld(px, py) {
  const ix = IMG.left + (px / 100) * (IMG.right - IMG.left);
  const iy = IMG.top + (py / 100) * (IMG.bottom - IMG.top);
  const u = ix / IMG.w;
  const v = iy / IMG.h;
  return { x: (u - 0.5) * PLANE_W, y: 0, z: (v - 0.5) * PLANE_H };
}

// Printed sheet fractions, origin bottom-left, y up (same as the PDF). High y is north, −z.
export function sheetToWorld(nx, ny) {
  return { x: (nx - 0.5) * BOARD_W, y: 0, z: (0.5 - ny) * BOARD_H };
}

// theta = 0, phi from +y. phi is kept away from 0 so the view is never straight down.
export function cameraOffset(theta, phi, dist) {
  return {
    x: dist * Math.sin(phi) * Math.sin(theta),
    y: dist * Math.cos(phi),
    z: dist * Math.sin(phi) * Math.cos(theta),
  };
}

export function flatForward(offset) {
  const x = -offset.x;
  const z = -offset.z;
  const len = Math.hypot(x, z) || 1;
  return { x: x / len, y: 0, z: z / len };
}

export function cross(a, b) {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x,
  };
}

// −z is the pawn front. rotation.y > 0 turns counter-clockwise from above.
// Face east (1, 0, 0): atan2(−1, −0) = −π/2, and local −z lands on +x.
export function yawFacing(dx, dz) {
  const len = Math.hypot(dx, dz);
  if (len < 1e-8) return 0;
  return Math.atan2(-dx / len, -dz / len);
}

export function travelPoint(a, b, t) {
  return {
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
    z: a.z + (b.z - a.z) * t,
  };
}

export function mapViewChecks() {
  const north = paperToWorld(50, 0);
  const east = paperToWorld(100, 50);
  const south = paperToWorld(50, 100);
  const veln = paperToWorld(22, 65);
  const center = paperToWorld(50, 50);
  const cam = cameraOffset(0, 1, 10);
  const fwd = flatForward(cam);
  const right = cross(fwd, UP);
  const high = sheetToWorld(0.5, 0.9);
  const left = sheetToWorld(0.1, 0.5);
  const faceEast = yawFacing(1, 0);
  const faceNorth = yawFacing(0, -1);
  return {
    northIsNegativeZ: north.z < center.z && north.z < 0,
    southIsPositiveZ: south.z > center.z,
    eastIsPositiveX: east.x > center.x && east.x > 0,
    velnIsSouthwest: veln.x < center.x && veln.z > center.z,
    cameraSitsSouth: cam.z > 0 && Math.abs(cam.x) < 1e-9 && cam.y > 0,
    looksNorth: fwd.z < -0.9 && Math.abs(fwd.x) < 1e-6,
    rightIsEast: right.x > 0.9 && Math.abs(right.y) < 1e-6 && Math.abs(right.z) < 1e-6,
    sheetHighIsNorth: high.z < 0,
    sheetLeftIsWest: left.x < 0,
    faceNorthIsZero: Math.abs(faceNorth) < 1e-9,
    faceEastIsMinusHalfPi: Math.abs(faceEast + Math.PI / 2) < 1e-9,
    travelMidpoint: (() => {
      const m = travelPoint({ x: 0, y: 0, z: 0 }, { x: 4, y: 2, z: -4 }, 0.5);
      return m.x === 2 && m.y === 1 && m.z === -2;
    })(),
  };
}

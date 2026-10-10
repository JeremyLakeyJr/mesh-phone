#!/usr/bin/env python3
"""Uniform single-ended RF line screening; not a fabricator or RF match approval.

Finite-volume quasi-TEM model, Z0=1/(c*sqrt(C*C_air)). Nominal JLC04161H-7628
outer dielectric/copper; approximate mask. Optional adjacent grounded copper.
"""
import argparse,json,math
import numpy as np
EPS0=8.8541878128e-12;C=299792458

def estimate(step=.005,width=.35,gap=None,span=2.,height=1.5):
 if step<=0 or width<=0 or (gap is not None and gap<=0):raise ValueError('positive dimensions required')
 x=np.arange(-span,span+step/2,step);y=np.arange(0,height+step/2,step)
 xx,yy=np.meshgrid(x,y);h=round(.2104/step)*step;t=round(.035/step)*step
 signal=(np.abs(xx)<=width/2+1e-8)&(yy>=h-1e-8)&(yy<=h+t+1e-8)
 side=np.zeros(xx.shape,dtype=bool) if gap is None else (np.abs(xx)>=width/2+gap-1e-8)&(yy>=h-1e-8)&(yy<=h+t+1e-8)
 known=np.zeros(xx.shape);known[signal]=1;fixed=signal|side
 fixed[0,:]=True;fixed[-1,:]=True;fixed[:,0]=True;fixed[:,-1]=True
 def solve(air):
  er=np.ones(xx.shape)
  if not air:
   er[yy<h]=4.4
   mask=(yy>=h)&(yy<h+.03048)
   mask|=(np.abs(xx)<=width/2)&(yy>=h)&(yy<h+t+.01524)
   if gap is not None:mask|=(np.abs(xx)>=width/2+gap)&(yy>=h)&(yy<h+t+.01524)
   er[mask]=3.8
  metal=signal|side;er[metal]=1
  ex=2*er[:,:-1]*er[:,1:]/(er[:,:-1]+er[:,1:]);ey=2*er[:-1,:]*er[1:,:]/(er[:-1,:]+er[1:,:])
  a=metal[:,:-1]&~metal[:,1:];ex[a]=er[:,1:][a]
  a=~metal[:,:-1]&metal[:,1:];ex[a]=er[:,:-1][a]
  a=metal[:-1,:]&~metal[1:,:];ey[a]=er[1:,:][a]
  a=~metal[:-1,:]&metal[1:,:];ey[a]=er[:-1,:][a]
  diagonal=np.zeros(xx.shape);diagonal[:,:-1]+=ex;diagonal[:,1:]+=ex;diagonal[:-1,:]+=ey;diagonal[1:,:]+=ey
  def apply(v):
   z=diagonal*v;z[:,:-1]-=ex*v[:,1:];z[:,1:]-=ex*v[:,:-1];z[:-1,:]-=ey*v[1:,:];z[1:,:]-=ey*v[:-1,:];z[fixed]=0;return z
  rhs=-apply(known);v=np.zeros(xx.shape);r=rhs.copy();direction=r/diagonal;rz=np.sum(r*direction);initial=np.sqrt(np.sum(rhs*rhs))
  for iteration in range(6000):
   ad=apply(direction);alpha=rz/np.sum(direction*ad);v+=alpha*direction;r-=alpha*ad
   if np.sqrt(np.sum(r*r))<initial*1e-9:break
   z=r/diagonal;new=np.sum(r*z);direction=z+(new/rz)*direction;rz=new
  else:raise RuntimeError('field solve did not converge')
  v+=known
  flux=diagonal*v;flux[:,:-1]-=ex*v[:,1:];flux[:,1:]-=ex*v[:,:-1];flux[:-1,:]-=ey*v[1:,:];flux[1:,:]-=ey*v[:-1,:]
  return float(np.sum(flux[signal])*EPS0),iteration+1
 actual,iterations=solve(False);air,air_iterations=solve(True)
 return dict(width_mm=width,coplanar_gap_mm=gap,grid_mm=step,domain_half_width_mm=span,domain_height_mm=height,
  rounded_dielectric_height_mm=h,capacitance_F_per_m=actual,air_capacitance_F_per_m=air,
  single_ended_ohms=1/(C*math.sqrt(actual*air)),iterations=[iterations,air_iterations],
  scope='Uniform infinite line only; rectangular copper, approximate solder mask, nominal Dk, finite grounded boundaries. Excludes coupling to other signals, pads, bends, vias, plane slots, etch/material tolerance and component impedances. Fabricator calculation/coupon and RF qualification required.',fabricator_approved=False)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--step',type=float,default=.005);a.add_argument('--width',type=float,default=.35);a.add_argument('--gap',type=float);a.add_argument('--span',type=float,default=2);a.add_argument('--height',type=float,default=1.5);args=a.parse_args()
 print(json.dumps(estimate(args.step,args.width,args.gap,args.span,args.height),indent=2))

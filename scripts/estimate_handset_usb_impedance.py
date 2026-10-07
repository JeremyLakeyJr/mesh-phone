#!/usr/bin/env python3
"""2-D quasi-TEM screening of the proposed uniform USB microstrip cross-section.

Finite-volume Laplace solve, odd-mode conductors at +/-1 V; ground/boundary 0 V.
Zdiff = 2/(c*sqrt(Codd*Codd_air)). Not a fabricator field-solver approval.
Dimensions/material inputs: https://jlcpcb.com/impedance (JLC04161H-7628).
"""
import argparse,json,math
import numpy as np
EPS0=8.8541878128e-12;C=299792458

def estimate(step=.005,width=.29,gap=.21):
 x=np.arange(-2,2+step/2,step);y=np.arange(0,1.5+step/2,step)
 xx,yy=np.meshgrid(x,y);h=round(.2104/step)*step;t=round(.035/step)*step
 pos=(xx>=gap/2-1e-8)&(xx<=gap/2+width+1e-8)&(yy>=h-1e-8)&(yy<=h+t+1e-8)
 neg=np.fliplr(pos)
 known=np.zeros(xx.shape);known[pos]=1;known[neg]=-1
 fixed=pos|neg;fixed[0,:]=True;fixed[-1,:]=True;fixed[:,0]=True;fixed[:,-1]=True
 def solve(air):
  er=np.ones(xx.shape)
  if not air:
   er[yy<h]=4.4
   mask=(yy>=h)&(yy<h+.03048)
   mask|=(np.abs(xx)>=gap/2)&(np.abs(xx)<=gap/2+width)&(yy>=h)&(yy<h+t+.01524)
   er[mask]=3.8
  # Conductors have no dielectric volume; edge flux uses the adjacent medium.
  er[pos|neg]=1
  ex=2*er[:,:-1]*er[:,1:]/(er[:,:-1]+er[:,1:]);ey=2*er[:-1,:]*er[1:,:]/(er[:-1,:]+er[1:,:])
  for conductor in [pos,neg]:
   a=conductor[:,:-1]&~conductor[:,1:];ex[a]=er[:,1:][a]
   a=~conductor[:,:-1]&conductor[:,1:];ex[a]=er[:,:-1][a]
   a=conductor[:-1,:]&~conductor[1:,:];ey[a]=er[1:,:][a]
   a=~conductor[:-1,:]&conductor[1:,:];ey[a]=er[:-1,:][a]
  diagonal=np.zeros(xx.shape);diagonal[:,:-1]+=ex;diagonal[:,1:]+=ex;diagonal[:-1,:]+=ey;diagonal[1:,:]+=ey
  def apply(v):
   z=diagonal*v;z[:,:-1]-=ex*v[:,1:];z[:,1:]-=ex*v[:,:-1];z[:-1,:]-=ey*v[1:,:];z[1:,:]-=ey*v[:-1,:];z[fixed]=0;return z
  rhs=-apply(known);v=np.zeros(xx.shape);r=rhs.copy();direction=r/diagonal;rz=np.sum(r*direction);initial=np.linalg.norm(rhs)
  for iteration in range(4000):
   ad=apply(direction);alpha=rz/np.sum(direction*ad);v+=alpha*direction;r-=alpha*ad
   if np.sqrt(np.sum(r*r))<initial*1e-9:break
   z=r/diagonal;new=np.sum(r*z);direction=z+(new/rz)*direction;rz=new
  else:raise RuntimeError('Field solve did not converge')
  v+=known
  flux=diagonal*v;flux[:,:-1]-=ex*v[:,1:];flux[:,1:]-=ex*v[:,:-1];flux[:-1,:]-=ey*v[1:,:];flux[1:,:]-=ey*v[:-1,:]
  return float(np.sum(flux[pos])*EPS0),iteration+1
 actual,iterations=solve(False);air,air_iterations=solve(True)
 return dict(width_mm=width,gap_mm=gap,grid_mm=step,rounded_dielectric_height_mm=h,odd_capacitance_F_per_m=actual,air_odd_capacitance_F_per_m=air,differential_ohms=2/(C*math.sqrt(actual*air)),iterations=[iterations,air_iterations],scope='Uniform infinite line only; rectangular copper, approximate solder mask, nominal Dk, finite boundaries. Excludes pads, bends, vias, plane slots, etch/tolerance and glass weave. Fabricator calculation/coupon required.',fabricator_approved=False)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--step',type=float,default=.005);a.add_argument('--width',type=float,default=.29);a.add_argument('--gap',type=float,default=.21);args=a.parse_args();print(json.dumps(estimate(args.step,args.width,args.gap),indent=2))

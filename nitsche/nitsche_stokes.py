from dolfin import *
import numpy as np

def normalize_vector(U):
  """
  Create a normalized vector of the UFL vector <U>.
  """
  # iterate through each component and convert to array :
  U_v = []
  for u in U:
    # convert to array and normailze the components of U :
    u_v = u.vector().array()
    U_v.append(u_v)
  U_v = np.array(U_v)

  # calculate the norm :
  norm_u = np.sqrt(sum(U_v**2))
  
  # normalize the vector :
  U_v /= norm_u
  
  # convert back to fenics :
  U_f = []
  for u_v in U_v:
    u_f = Function(Q)
    u_f.vector().set_local(u_v)
    u_f.vector().apply('insert')
    U_f.append(u_f)

  # return a UFL vector :
  return as_vector(U_f)

def vert_integrate(u, Q, ff):
  """
  Integrate <u> from the bed to the surface.
  """
  phi    = TestFunction(Q)               # test function
  v      = TrialFunction(Q)              # trial function
  bc     = DirichletBC(Q, 0.0, ff, 2)    # integral is zero on bed (ff = 2) 
  a      = v.dx(2) * phi * dx            # rhs
  L      = u * phi * dx                # lhs
  v      = Function(Q)                   # solution function
  solve(a == L, v, bc)                   # solve
  return v

def extrude(f, b, d, Q, ff):
  """
  This extrudes a function <f> defined along a boundary <b> out onto
  the domain in the direction <d>.  It does this by formulating a 
  variational problem:
  """
  phi = TestFunction(Q)
  v   = TrialFunction(Q)
  a   = v.dx(d) * phi * dx
  L   = DOLFIN_EPS * phi * dx
  bc  = DirichletBC(Q, f, ff, b)
  v   = Function(Q)
  solve(a == L, v, bc)
  return v

def epsilon(U):
  """
  return the strain-rate tensor of <U>.
  """
  u,v,w = U
  epi   = 0.5 * (grad(U) + grad(U).T)
  epi02 = 0.5*u.dx(2)
  epi12 = 0.5*v.dx(2)
  epsdot = as_matrix([[epi[0,0],  epi[0,1],  epi02   ],
                      [epi[1,0],  epi[1,1],  epi12   ],
                      [epi02,     epi12,     epi[2,2]]])
  return epsdot

#top     = Point(0.0, 0.0, 1.0)
#bot     = Point(0.0, 0.0, 0.0)
#cone    = Cone(top, bot, 1.0, 1.0)
#mesh    = Mesh(cone,20)
#nx      = 20
#ny      = 20
#nz      = 4
#mesh    = BoxMesh(-1,-1, 0, 1, 1, 1, nx,ny,nz)
mesh    = Mesh('../meshes/unit_cyl_mesh.xml')

# Define function spaces
B  = FunctionSpace(mesh, "B", 4)
Q  = FunctionSpace(mesh, "CG", 1)
M  = Q + B
V  = MixedFunctionSpace([M,M,M])
W  = MixedFunctionSpace([V,Q])
ff = FacetFunction('size_t', mesh, 0)

# iterate through the facets and mark each if on a boundary :
#
#   1 = high slope, upward facing ................ surface
#   2 = high slope, downward facing .............. base
#   3 = low slope, upward or downward facing ..... side
for f in facets(mesh):
  n       = f.normal()    # unit normal vector to facet f
  tol     = 1.0
  if   n.z() >=  tol and f.exterior():
    ff[f] = 1
  elif n.z() <= -tol and f.exterior():
    ff[f] = 2
  elif abs(n.z()) < tol and f.exterior():
    ff[f] = 3

ds       = Measure('ds')[ff]
dSrf     = ds(1)
dBed     = ds(2)
dGamma   = ds(3)
dG_0     = dBed

t       = 1000000.0 / 2
S0      = 200.0
bm      = 1000.0

def gauss(x, y, sigx, sigy):
  return exp(-((x/(2*sigx))**2 + (y/(2*sigy))**2))

class Surface(Expression):
  def eval(self,values,x):
    values[0] = S0 + 1200*gauss(x[0], x[1], t/2, t/2)
S = Surface(element = Q.ufl_element())

class Bed(Expression):
  def eval(self,values,x):
    values[0] = S0 - 500.0 \
                - 1000.0 * gauss(x[0], x[1], t/2, t/2)
B = Bed(element = Q.ufl_element())

class Depth(Expression):
  def eval(self, values, x):
    values[0] = min(0, x[2])
D = Depth(element = Q.ufl_element())

class Beta(Expression):
  def eval(self, values, x):
    values[0] = bm * gauss(x[0], x[1], t/2, t/2)
fric = Beta(element = Q.ufl_element())

xmin = -t
xmax = t
ymin = -t
ymax = t

# width and origin of the domain for deforming x coord :
width_x  = xmax - xmin
offset_x = xmin

# width and origin of the domain for deforming y coord :
width_y  = ymax - ymin
offset_y = ymin

# Deform the square to the defined geometry :
for x in mesh.coordinates():
  # transform x :
  x[0]  = x[0]  * width_x

  # transform y :
  x[1]  = x[1]  * width_y

  # transform z :
  # thickness = surface - base, z = thickness + base
  x[2]  = x[2] * (S(x[0], x[1], x[2]) - B(x[0], x[1], x[2]))
  x[2]  = x[2] +  B(x[0], x[1], x[2])

# constants :
p0     = 101325
cp     = 1007
T0     = 288.15
M      = 0.0289644
rho    = 917.0
rho_w  = 1000.0
g      = 9.80665
gamma  = 8.71e-4
E      = 1.0
R      = 8.31447
n      = 3.0
theta  = 268.0
x      = SpatialCoordinate(mesh)

# solver parameters :
parameters['form_compiler']['quadrature_degree'] = 3
params = {"newton_solver":
         {"linear_solver"        : 'mumps',
          "preconditioner"       : 'default',
          "maximum_iterations"   : 35,
          "relaxation_parameter" : 1.0,
          "relative_tolerance"   : 1e-3,
          "absolute_tolerance"   : 1e-16}}

#===============================================================================
# define variational problem :
G   = Function(W)
dU  = TrialFunction(W)
Tst = TestFunction(W)

du,  dp = split(dU)
U,   p  = split(G)
Phi, xi = split(Tst)

u,   v,   w   = U
phi, psi, chi = Phi

# rate-factor :
a_T   = conditional( lt(theta, 263.15), 1.1384496e-5, 5.45e10)
Q_T   = conditional( lt(theta, 263.15), 6e4,          13.9e4)
A     = E * a_T * exp( -Q_T / (R * theta))
b     = A**(-1/n)

k   = as_vector([0, 0, 1])
f_w = rho*g*(S - x[2]) + rho_w*g*D
p_a = p0 * (1 - g*x[2]/(cp*T0))**(cp*M/R)
u_n = Constant(0.0)
u_0 = Expression(("0.0","0.0","0.0"), element=V.ufl_element())
p_0 = Constant(0.0)

# Second invariant of the strain rate tensor squared
epi   = epsilon(U)
ep_xx = epi[0,0]
ep_yy = epi[1,1]
ep_xy = epi[0,1]
ep_xz = epi[0,2]
ep_yz = epi[1,2]

epsdot = ep_xx**2 + ep_yy**2 + ep_xx*ep_yy + ep_xy**2 + ep_xz**2 + ep_yz**2
eta    = 0.5 * b * (epsdot + 1e-10)**((1-n)/(2*n))
#eta    = Constant(1e8)

alpha = Constant(1.0/10)
beta  = Constant(100.0)
h     = CellSize(mesh)
n     = FacetNormal(mesh)
I     = Identity(3)
fric  = Constant(0.01)
f     = rho*g*k

bc2 = DirichletBC(W.sub(0), u_0, ff, 2)
bc3 = DirichletBC(W.sub(0).sub(2), 0.0, ff, 2)
bc1 = DirichletBC(W.sub(1), p_0, ff, 1)
bcs = [bc1]

#a = dot(grad(xi), N) * dot(grad(dp), N) * ds
#b = inner(grad(xi), grad(dp)) * dx
#
#A = PETScMatrix()
#B = PETScMatrix()
#
#A = assemble(a, tensor=A)
#B = assemble(b, tensor=B)
#eigensolver = SLEPcEigenSolver(A,B)
#eigensolver.solve()
#
#C = eigensolver.get_eigenvalue()[0]

def epsilon(u): return 0.5*(grad(u) + grad(u).T)
def sigma(u,p): return 2*eta*epsilon(u) - p*I
def L(u,p):     return -div(sigma(u,p))

B_o = + inner(sigma(U,p), grad(Phi)) * dx \
      - div(U) * xi * dx \
      - alpha * h**2 * inner(L(U,p), L(Phi,xi)) * dx \

B_g = - dot(Phi,n) * dot(n, dot(sigma(U,  p ), n)) * dG_0 \
      - dot(U,  n) * dot(n, dot(sigma(Phi,xi), n)) * dG_0 \
      + beta/h * dot(U,n) * dot(Phi,n) * dG_0 \
      - fric**2 * dot(U, Phi) * dBed \
      + f_w * dot(Phi, n) * dGamma \

F   = + dot(f,Phi)*dx \
      + alpha * h**2 * inner(f, L(Phi,xi)) * dx \
      - u_n * dot(n, dot(sigma(Phi,xi), n)) * dG_0 \
      + beta/h * u_n * dot(Phi,n) * dG_0 \

R = B_o + B_g - F

J = derivative(R, G, dU)

# compute solution :
solve(R == 0, G, bcs, J=J, solver_parameters=params)

File("output/U.pvd")    << project(U)
File("output/P.pvd")    << project(p)
File("output/divU.pvd") << project(div(U))
File("output/beta.pvd") << interpolate(beta,Q)


#===============================================================================
# change to U-coordinate system, solve for directional derivative velocity :
Q2 = MixedFunctionSpace([Q,Q])

Phi      = TestFunction(Q2)
phi, psi = Phi
dU       = TrialFunction(Q2)
du, dv   = dU

U        = as_vector([project(u), project(v)])
U_nm     = normalize_vector(U)
U        = as_vector([U[0],     U[1],  ])
U_n      = as_vector([U_nm[0],  U_nm[1]])
U_t      = as_vector([U_nm[1], -U_nm[0]])

u_s     = dot(dU, U_n)
v_s     = dot(dU, U_t)
U_s     = as_vector([u_s,       v_s      ])
gradu   = as_vector([u_s.dx(0), u_s.dx(1)])
gradv   = as_vector([v_s.dx(0), v_s.dx(1)])
dudn    = dot(gradu, U_n)
dudt    = dot(gradu, U_t)
dudz    = u_s.dx(2)
dvdn    = dot(gradv, U_n)
dvdt    = dot(gradv, U_t)
dvdz    = v_s.dx(2)
gradphi = as_vector([phi.dx(0), phi.dx(1)])
gradpsi = as_vector([psi.dx(0), psi.dx(1)])
gradS   = as_vector([S.dx(0),   S.dx(1)  ])
dphidn  = dot(gradphi, U_n)
dphidt  = dot(gradphi, U_t)
dpsidn  = dot(gradpsi, U_n)
dpsidt  = dot(gradpsi, U_t)
dSdn    = dot(gradS,   U_n)
dSdt    = dot(gradS,   U_t)
gradphi = as_vector([dphidn,    dphidt,  phi.dx(2)])
gradpsi = as_vector([dpsidn,    dpsidt,  psi.dx(2)])
gradS   = as_vector([dSdn,      dSdt,    S.dx(2)  ])

epi_1  = as_vector([2*dudn + dvdt, 
                    0.5*(dudt + dvdn),
                    0.5*dudz             ])
epi_2  = as_vector([0.5*(dudt + dvdn),
                         dudn + 2*dvdt,
                    0.5*dvdz             ])

tau_dn = phi * rho * g * gradS[0] * dx
tau_dt = psi * rho * g * gradS[1] * dx

tau_bn = beta**2 * u_s * phi * dBed
tau_bt = beta**2 * v_s * psi * dBed

tau_pn = - f_w * n[0] * phi * dGamma
tau_pt = - f_w * n[1] * psi * dGamma

tau_nn = 2 * eta * epi_1[0] * gradphi[0] * dx
tau_nt = 2 * eta * epi_1[1] * gradphi[1] * dx
tau_nz = 2 * eta * epi_1[2] * gradphi[2] * dx

tau_tn = 2 * eta * epi_2[0] * gradpsi[0] * dx
tau_tt = 2 * eta * epi_2[1] * gradpsi[1] * dx
tau_tz = 2 * eta * epi_2[2] * gradpsi[2] * dx

tau_n  = tau_nn + tau_nt + tau_nz + tau_bn + tau_pn - tau_dn
tau_t  = tau_tn + tau_tt + tau_tz + tau_bt + tau_pt - tau_dt

delta  = tau_n + tau_t
U_s    = Function(Q2)

bc1 = DirichletBC(Q2, U, ff, 5)
bc2 = DirichletBC(Q2, U, ff, 6)
bc3 = DirichletBC(Q2, U, ff, 3)
bcs = [bc1, bc2, bc3]
bcs = []

solve(lhs(delta) == rhs(delta), U_s, bcs)

#File('output/U_solve.pvd') << U_s

#===============================================================================
# solve with corrected velociites :
phi     = TestFunction(Q)
dtau    = TrialFunction(Q)
        
u_s     = dot(U_s, U_n)
v_s     = dot(U_s, U_t)
U_s     = as_vector([u_s,       v_s      ])
gradu   = as_vector([u_s.dx(0), u_s.dx(1)])
gradv   = as_vector([v_s.dx(0), v_s.dx(1)])
dudn    = dot(gradu, U_n)
dudt    = dot(gradu, U_t)
dudz    = u_s.dx(2)
dvdn    = dot(gradv, U_n)
dvdt    = dot(gradv, U_t)
dvdz    = v_s.dx(2)
gradphi = as_vector([phi.dx(0), phi.dx(1)])
gradS   = as_vector([S.dx(0),   S.dx(1)  ])
dphidn  = dot(gradphi, U_n)
dphidt  = dot(gradphi, U_t)
dSdn    = dot(gradS,   U_n)
dSdt    = dot(gradS,   U_t)
gradphi = as_vector([dphidn, dphidt, phi.dx(2)])
gradS   = as_vector([dSdn,   dSdt,   S.dx(2)  ])

epi_1  = as_vector([2*dudn + dvdt, 
                    0.5*(dudt + dvdn),
                    0.5*dudz             ])
epi_2  = as_vector([0.5*(dudt + dvdn),
                         dudn + 2*dvdt,
                    0.5*dvdz             ])

tau_dn = phi * rho * g * gradS[0] * dx
tau_dt = phi * rho * g * gradS[1] * dx

tau_bn = beta**2 * u_s * phi * dBed
tau_bt = beta**2 * v_s * phi * dBed

tau_pn = - f_w * n[0] * phi * dGamma
tau_pt = - f_w * n[1] * phi * dGamma

tau_nn = 2 * eta * epi_1[0] * gradphi[0] * dx
tau_nt = 2 * eta * epi_1[1] * gradphi[1] * dx
tau_nz = 2 * eta * epi_1[2] * gradphi[2] * dx

tau_tn = 2 * eta * epi_2[0] * gradphi[0] * dx
tau_tt = 2 * eta * epi_2[1] * gradphi[1] * dx
tau_tz = 2 * eta * epi_2[2] * gradphi[2] * dx

# mass matrix :
M = assemble(phi*dtau*dx)

# assemble the vectors :
tau_dn_v = assemble(tau_dn)
tau_dt_v = assemble(tau_dt)
tau_bn_v = assemble(tau_bn)
tau_bt_v = assemble(tau_bt)
tau_pn_v = assemble(tau_pn)
tau_pt_v = assemble(tau_pt)
tau_nn_v = assemble(tau_nn)
tau_nt_v = assemble(tau_nt)
tau_nz_v = assemble(tau_nz)
tau_tn_v = assemble(tau_tn)
tau_tt_v = assemble(tau_tt)
tau_tz_v = assemble(tau_tz)

# solution functions :
tau_dn   = Function(Q)
tau_dt   = Function(Q)
tau_bn   = Function(Q)
tau_bt   = Function(Q)
tau_pn   = Function(Q)
tau_pt   = Function(Q)
tau_bt   = Function(Q)
tau_nn   = Function(Q)
tau_nt   = Function(Q)
tau_nz   = Function(Q)
tau_tn   = Function(Q)
tau_tt   = Function(Q)
tau_tz   = Function(Q)

# solve the linear system :
solve(M, tau_dn.vector(), tau_dn_v)
solve(M, tau_dt.vector(), tau_dt_v)
solve(M, tau_bn.vector(), tau_bn_v)
solve(M, tau_bt.vector(), tau_bt_v)
solve(M, tau_pn.vector(), tau_pn_v)
solve(M, tau_pt.vector(), tau_pt_v)
solve(M, tau_nn.vector(), tau_nn_v)
solve(M, tau_nt.vector(), tau_nt_v)
solve(M, tau_nz.vector(), tau_nz_v)
solve(M, tau_tn.vector(), tau_tn_v)
solve(M, tau_tt.vector(), tau_tt_v)
solve(M, tau_tz.vector(), tau_tz_v)

memb_n   = as_vector([tau_nn, tau_nt, tau_nz])
memb_t   = as_vector([tau_tn, tau_tt, tau_tz])
memb_x   = tau_nn + tau_nt + tau_nz
memb_y   = tau_tn + tau_tt + tau_tz
membrane = as_vector([memb_x, memb_y, 0.0])
driving  = as_vector([tau_dn, tau_dt, 0.0])
basal    = as_vector([tau_bn, tau_bt, 0.0])
pressure = as_vector([tau_pn, tau_pt, 0.0])

tot      = membrane + basal + pressure - driving

#File("output/U_s.pvd")      << project(U_s)
File("output/memb_n.pvd")   << project(memb_n)
File("output/memb_t.pvd")   << project(memb_t)
File("output/membrane.pvd") << project(membrane)
File("output/driving.pvd")  << project(driving)
File("output/basal.pvd")    << project(basal)
File("output/pressure.pvd") << project(pressure)
File("output/total.pvd")    << project(tot)

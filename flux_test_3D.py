from pylab    import *
from fenics   import *
from matrices import plot_matrix

<<<<<<< HEAD
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

=======
>>>>>>> 4bd5240e2c2a7668595cbabf9877c8c059b229f9
n     = 10
mesh  = UnitCubeMesh(n,n,n)
#mesh = Mesh('meshes/unit_cube_mesh.xml')
bmesh = BoundaryMesh(mesh, 'exterior')

# refine mesh :
origin = Point(0.0,0.5,0.5)
for i in range(1,1):
  cell_markers = CellFunction("bool", mesh)
  cell_markers.set_all(False)
  for cell in cells(mesh):
    p = cell.midpoint()
    if p.distance(origin) < 1.0/i:
      cell_markers[cell] = True
  mesh = refine(mesh, cell_markers)

Q = FunctionSpace(mesh, 'CG', 1)
V = VectorFunctionSpace(mesh, 'CG', 1)
H = CellSize(mesh)
N = FacetNormal(mesh)
A = FacetArea(mesh)

w = TrialFunction(Q)
v = TestFunction(Q)
u = Function(Q, name='u')

f = Constant(1.0)

a = inner(grad(w), grad(v)) * dx
l = f * v * dx

def left(x, on_boundary):
  return x[0] == 0 and on_boundary

def right(x, on_boundary):
  return x[0] == 1 and on_boundary

def top(x, on_boundary):
  return x[1] == 1 and on_boundary

def bottom(x, on_boundary):
  return x[1] == 0 and on_boundary

bcl = DirichletBC(Q, 0.0, left)
bcr = DirichletBC(Q, 0.0, right)
bct = DirichletBC(Q, 0.0, top)
bcb = DirichletBC(Q, 0.0, bottom)

solve(a == l, u, bcl)

File('output/u.pvd') << u

uv = u.vector().array()

<<<<<<< HEAD
#N = as_vector([-1,0,0])

M  = assemble(w * v * dx)

nx_v = assemble(v * N[0] * ds)
ny_v = assemble(v * N[1] * ds)
nz_v = assemble(v * N[2] * ds)

nx = Function(Q)
ny = Function(Q)
nz = Function(Q)

solve(M, nx.vector(), nx_v)
solve(M, ny.vector(), ny_v)
solve(M, nz.vector(), nz_v)


n  = as_vector([nx,ny,nz])

#n  = normalize_vector(n)

File('output/n.pvd') << project(n,V)

s  = assemble(-dot(grad(u), N) * v * ds)
=======
#N  = as_vector([-1,0,0])

M  = assemble(w * v * dx)

sx = u.dx(0) * N[0] * v * ds 
sy = u.dx(1) * N[1] * v * ds 
sz = u.dx(2) * N[2] * v * ds 

sx_v = assemble(sx)
sy_v = assemble(sy)
sz_v = assemble(sz)

sx = Function(Q)
sy = Function(Q)
sz = Function(Q)

#s  = assemble(-dot(grad(u), N) * v * dx)
>>>>>>> 4bd5240e2c2a7668595cbabf9877c8c059b229f9
b  = assemble(l)
K  = assemble(a)
h  = project(H,Q).vector().array()/1.2

t  = 1/h**2*(np.dot(K.array(),uv) - b.array())

q = Function(Q, name='q')
q.vector().set_local(t)
q.vector().apply('insert')

File('output/q.pvd') << q

solve(M, sx.vector(), sx_v)
solve(M, sy.vector(), sy_v)
solve(M, sz.vector(), sz_v)

s = as_vector([sx, sy, sz])

File('output/fx.pvd') << project(s,V)

#fx = Function(Q, name='fx')
#solve(M, fx.vector(), s)
#File('output/fx.pvd') << fx

fig = figure(figsize=(10,5))
ax1 = fig.add_subplot(121)
ax2 = fig.add_subplot(122)

plot_matrix(M.array(), ax1, r'mass matrix $M$',      continuous=True)
plot_matrix(K.array(), ax2, r'stiffness matrix $K$', continuous=True)

tight_layout()
show()




from pylab    import *
from fenics   import *
from matrices import plot_matrix

n    = 2
#mesh = UnitIntervalMesh(3)
#mesh = UnitSquareMesh(n,n)
#mesh = UnitCubeMesh(n,n,n)
#mesh = Mesh('meshes/unit_square_mesh.xml')
#mesh = Mesh('meshes/unit_cube_mesh.xml')
mesh = Mesh('meshes/triangle.xml')

## refine mesh :
#origin = Point(0.0,0.0,0.0)
#for i in range(1,10):
#  cell_markers = CellFunction("bool", mesh)
#  cell_markers.set_all(False)
#  for cell in cells(mesh):
#    p = cell.midpoint()
#    if p.distance(origin) < 1.0/i:
#      cell_markers[cell] = True
#  mesh = refine(mesh, cell_markers)

## refine mesh :
#for i in range(1,10):
#  cell_markers = CellFunction("bool", mesh)
#  cell_markers.set_all(False)
#  for cell in cells(mesh):
#    p = cell.midpoint()
#    if p.y() <= 1.0/i:
#      cell_markers[cell] = True
#  mesh = refine(mesh, cell_markers)

Q = FunctionSpace(mesh, 'CG', 1)
V = VectorFunctionSpace(mesh, 'CG', 1)

w = TrialFunction(Q)
v = TestFunction(Q)
u = Function(Q, name='u')

f = Constant(1.0)

a = w.dx(0) * v.dx(0) * dx
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

bc  = [bct, bcr]

solve(a == l, u, bc)

File('output/u.pvd') << u

uv = u.vector().array()
b  = assemble(l).array()
A  = assemble(a).array()
h  = project(CellSize(mesh),Q).vector().array()

t  = np.dot(A,uv) - b

q = Function(Q, name='q')
q.vector().set_local(t)
q.vector().apply('insert')

File('output/q.pvd') << q

K = array([[ 1,-1, 0, 0, 0, 0],
           [-1, 4,-2,-1, 0, 0],
           [ 0,-2, 4, 0,-2, 0],
           [ 0,-1, 0, 2,-1, 0],
           [ 0, 0,-2,-1, 4,-1],
           [ 0, 0, 0, 0,-1, 1]])

fig = figure()
ax  = fig.add_subplot(111)

plot_matrix(A, ax, r'stiffness matrix $K$', continuous=False)

tight_layout()
show()

from pylab import *

uv_r = dot(inv(0.5*K[:3,:3]), b[:3])
uv_r = append(uv_r, zeros(3))

u.vector().set_local(uv_r)
u.vector().apply('insert')

File('output/ur.pvd') << u





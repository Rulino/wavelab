import modulus.sym
from modulus.sym.hydra import ModulusConfig
from modulus.sym.domain import Domain
from modulus.sym.geometry.primitives_2d import Rectangle
from modulus.sym.key import Key
from modulus.sym.models.fully_connected import FullyConnectedArch
from modulus.sym.solver import Solver
from modulus.sym.domain.constraint import PointwiseInteriorConstraint
from sympy import symbols, sin, exp, sqrt, pi, Piecewise

@modulus.sym.main(config_path="config", config_name="config")
def run(cfg: ModulusConfig) -> None:
    # -------------------------
    # Definovanie symbolov
    # -------------------------
    x, y = symbols("x y", real=True)

    # -------------------------
    # Parametre
    # -------------------------
    # Air medium: low absorption
    absorption_air = 0.1
    # Prostredie wood: moderate absorption (lower than in concrete)
    absorption_wood = 1
    amplitude = 1.0
    lambda_val = 0.3
    # Vertical boundary between media – e.g. x < 1.5: air, x >= 1.5: wood
    boundary_x = 1.5

    # Coefficients for reflection and transmission
    # At the air-to-wood interface, transmission is higher (T = 0.8) a lower reflection (R = 0.2)
    R = 0.3
    T = 0.7

    # Antenna position (if the antenna moves, scattering adapts)
    x0, y0 = 0.75, 1

    # -------------------------
    # Air region (x < boundary_x)
    # -------------------------
    r_air = sqrt((x - x0)**2 + (y - y0)**2)
    u_air_direct = amplitude * sin(2*pi*r_air/lambda_val) * exp(-absorption_air*r_air)

    # Reflected wave: mirror image of the antenna across the boundary x = boundary_x
    x_ref = 2*boundary_x - x0
    y_ref = y0
    r_ref = sqrt((x - x_ref)**2 + (y - y_ref)**2)
    u_air_reflected = -amplitude * R * sin(2*pi*r_ref/lambda_val) * exp(-absorption_air*r_ref)

    u_expr_air = u_air_direct + u_air_reflected

    # -------------------------
    # Wood region (x >= boundary_x)
    # -------------------------
    # First compute the ray intersection from the antenna (x0, y0) with the vertical boundary x = boundary_x.
    eps = 1e-12  # to avoid division by zero
    slope = (y - y0) / ((x - x0) + eps)
    y_int = y0 + slope*(boundary_x - x0)

    # r_in: distance from the antenna to the boundary intersection
    r_in = sqrt((boundary_x - x0)**2 + (y_int - y0)**2)
    # r_out: distance od intersection k bodu (x, y)
    r_out = sqrt((x - boundary_x)**2 + (y - y_int)**2)
    total_path = r_in + r_out

    # Transmission term: wave transmitted into wood (with higher T and attenuation in wood)
    u_transmitted = amplitude * T * sin(2*pi*total_path/lambda_val) * exp(-absorption_wood*total_path)
    
    # Scattering term: additional contribution generated at the interface.
    # The scattering amplitude is computed z amplitude a absorption_wood:
    amplitude_scattered = amplitude * (absorption_wood / (absorption_wood + 1))
    u_scattered = amplitude_scattered * sin(2*pi*r_out/lambda_val) * exp(-absorption_wood*r_out)

    # The wood-region wave is sum of transmission and scattering
    u_expr_wood = u_transmitted + u_scattered

    # -------------------------
    # Combination cez Piecewise:
    # For x < boundary_x use air region, for x >= boundary_x use wood medium.
    # -------------------------
    u_expr = Piecewise(
        (u_expr_air, x < boundary_x),
        (u_expr_wood, True)
    )

    # -------------------------
    # Nastavenie PINN
    # -------------------------
    geom = Rectangle((0, 0), (3, 2))
    input_keys = [Key("x"), Key("y")]
    output_keys = [Key("u")]

    net = FullyConnectedArch(input_keys=input_keys, output_keys=output_keys)
    nodes = [net.make_node("wave")]

    wave_constraint = PointwiseInteriorConstraint(
        nodes=nodes,
        geometry=geom,
        outvar={"u": u_expr},
        batch_size=cfg.batch_size.Interior
    )

    domain = Domain()
    domain.add_constraint(wave_constraint, "wave_constraint")

    slv = Solver(cfg, domain)
    slv.solve()

if __name__ == "__main__":
    run()

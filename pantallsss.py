def calculate_ppi(resolution_width, resolution_height, diagonal_size_inch):
    # Calcula los PPI usando el teorema de Pitágoras
    diagonal_resolution = (resolution_width**2 + resolution_height**2) ** 0.5
    ppi = diagonal_resolution / diagonal_size_inch
    return ppi

if __name__ == "__main__":
    resolution_width = 4480
    resolution_height = 2520
    diagonal_size_inch = 23.5

    ppi = calculate_ppi(resolution_width, resolution_height, diagonal_size_inch)
    print(f"Screen resolution: {resolution_width} x {resolution_height}")
    print(f"Diagonal size: {diagonal_size_inch} inches")
    print(f"Calculated PPI: {ppi}")

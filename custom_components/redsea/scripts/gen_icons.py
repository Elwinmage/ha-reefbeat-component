import math
import os
import re
import sys

input_file = "icons.js"
output_dir = "svg_output"

if not os.path.exists(input_file):
    print(f"Erreur : Le fichier '{input_file}' est introuvable.")
    sys.exit(1)

with open(input_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Extraire le bloc contenant l'objet ICONS
match = re.search(r"const\s+ICONS\s*=\s*\{([^;]+)\};", content, re.DOTALL)
if not match:
    print("Erreur : Impossible de trouver l'objet 'ICONS'.")
    sys.exit(1)

icons_block = match.group(1)

# 2. Découper ligne par ligne ou par entrée pour gérer la concaténation par "+"
# On cherche les motifs de type "nom": "partie1" + "partie2" + ...
ICONS = {}
# Regex pour capturer la clé et tout le contenu de la valeur jusqu'à la virgule de fin ou la fin du bloc
entries = re.findall(
    r'"([^"]+)"\s*:\s*((?:(?!"\s*:\s*").)+?)(?=\n\s*"[a-zA-Z0-9_-]+"\s*:|\Z)',
    icons_block,
    re.DOTALL,
)

for name, raw_value in entries:
    # Nettoyer les sauts de ligne, les espaces superflus, et recoller les chaînes séparées par '+'
    # On extrait toutes les sous-chaînes entre guillemets
    string_parts = re.findall(r'"([^"]*)"', raw_value)
    full_path = "".join(string_parts)
    if full_path:
        ICONS[name] = full_path

if not ICONS:
    print("Erreur : Aucune icône n'a pu être extraite.")
    sys.exit(1)

os.makedirs(output_dir, exist_ok=True)
print(
    f"{len(ICONS)} icônes détectées (avec fusion des chaînes concaténées). Génération..."
)

# 3. Génération des fichiers SVG individuels
for name, path_data in ICONS.items():
    svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">\n  <path fill="currentColor" d="{path_data}" />\n</svg>'
    with open(os.path.join(output_dir, f"{name}.svg"), "w", encoding="utf-8") as f:
        f.write(svg_content)

# 4. Génération de la planche globale (planche-icones.svg)
cols = 3
cell_width = 240
cell_height = 50
padding = 20
header_height = 60

num_icons = len(ICONS)
rows = math.ceil(num_icons / cols)

total_width = cols * cell_width + padding * 2
total_height = header_height + rows * cell_height + padding * 2

svg_lines = []
svg_lines.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" width="100%">'
)
svg_lines.append("  <style>")
svg_lines.append("    .bg { fill: #0f172a; }")
svg_lines.append(
    '    .title { fill: #38bdf8; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 18px; font-weight: bold; }'
)
svg_lines.append(
    '    .subtitle { fill: #94a3b8; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 12px; }'
)
svg_lines.append("    .card-bg { fill: #1e293b; stroke: #334155; rx: 6px; ry: 6px; }")
svg_lines.append("    .icon-path { fill: #38bdf8; }")
svg_lines.append(
    "    .label { fill: #f8fafc; font-family: monospace; font-size: 12px; }"
)
svg_lines.append("  </style>")

svg_lines.append(
    f'  <rect width="{total_width}" height="{total_height}" class="bg" rx="8" />'
)

for i, (name, path_data) in enumerate(ICONS.items()):
    r = i // cols
    c = i % cols

    x = padding + c * cell_width
    y = header_height + padding + r * cell_height

    svg_lines.append(f'  <g transform="translate({x}, {y})">')
    svg_lines.append(
        f'    <rect width="{cell_width - 12}" height="{cell_height - 6}" class="card-bg" />'
    )
    svg_lines.append('    <g transform="translate(14, 13)">')
    svg_lines.append(f'      <path class="icon-path" d="{path_data}" />')
    svg_lines.append("    </g>")
    svg_lines.append(f'    <text x="48" y="30" class="label">redsea:{name}</text>')
    svg_lines.append("  </g>")

svg_lines.append("</svg>")

sheet_path = os.path.join(output_dir, "planche-icones.svg")
with open(sheet_path, "w", encoding="utf-8") as f:
    f.write("\n".join(svg_lines))

print(f"Succès ! Tout a été généré proprement dans '{output_dir}'.")

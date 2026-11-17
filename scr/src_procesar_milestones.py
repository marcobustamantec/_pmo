import yaml
import csv
import os

# Determinar las rutas usando el directorio actual del script
script_dir = os.path.dirname(os.path.abspath(__file__))
yml_path = os.path.join(script_dir, '../projects/test_01.yml')
csv_path = os.path.join(script_dir, '../projects/milestones_resumen.csv')

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

with open(yml_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

resumen = []

# Iterar sobre los milestones y calcular las sumas
for milestone in data.get('proyecto', {}).get('milestone', []):
    ms_nombre = milestone.get('nombre', 'Desconocido')
    suma_puntos = 0
    suma_dias = 0
    
    # Algunos milestones pueden no tener el campo 'wb' o estar vacío
    wb_list = milestone.get('wb') or []
    
    for wb in wb_list:
        suma_puntos += safe_int(wb.get('puntos'))
        suma_dias += safe_int(wb.get('dias'))
        
    resumen.append({
        'Milestone': ms_nombre,
        'Suma Puntos': suma_puntos,
        'Suma Dias': suma_dias
    })

# Exportar los datos sumarizados a CSV
with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=['Milestone', 'Suma Puntos', 'Suma Dias'])
    writer.writeheader()
    writer.writerows(resumen)

print(f"✅ Archivo generado con éxito en: {os.path.abspath(csv_path)}")

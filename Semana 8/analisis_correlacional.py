import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pymysql
import warnings
from scipy import stats

warnings.filterwarnings('ignore')

class AnalisisCorrelacional:
    def __init__(self):
        pass
        
    def conectar_bd(self):
        """Conexión a la base de datos"""
        return pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='',
            database='mermas'
        )

    def cargar_datos(self):
        """Cargar datos desde la base de datos"""
        connection = self.conectar_bd()
        
        query = """
        SELECT 
            fecha,
            linea,
            categoria,
            seccion,
            motivo,
            merma_unidad
        FROM mermasdb 
        WHERE merma_unidad IS NOT NULL 
        AND fecha IS NOT NULL
        AND categoria != 'insumos platos asadurias'
        ORDER BY fecha
        """

        data = pd.read_sql(query, connection)
        connection.close()
        
        print(f"Datos cargados: {len(data)} registros")
        return data

    def preprocesar_datos(self, data):
        """Preprocesamiento básico de datos"""
        print("🔧 Preprocesando datos...")
        
        # Convertir fecha
        data['fecha'] = pd.to_datetime(data['fecha'])
        
        # Crear variables temporales
        data['mes'] = data['fecha'].dt.month
        data['trimestre'] = data['fecha'].dt.quarter
        data['año'] = data['fecha'].dt.year
        data['dia_semana'] = data['fecha'].dt.dayofweek
        data['dia_mes'] = data['fecha'].dt.day
        data['semestre'] = (data['fecha'].dt.quarter <= 2).astype(int) + 1
        data['estacion'] = data['fecha'].dt.month % 12 // 3 + 1
        data['bimestre'] = (data['fecha'].dt.month - 1) // 2 + 1
        data['fin_semana'] = data['fecha'].dt.dayofweek.isin([5, 6]).astype(int)
        data['fin_mes'] = (data['fecha'].dt.day >= 25).astype(int)
        
        # Procesar mermas
        data['merma_unidad_abs'] = np.abs(data['merma_unidad'])
        
        # Crear variables categóricas numéricas
        for col in ['linea', 'categoria', 'seccion', 'motivo']:
            data[f'{col}_num'] = pd.Categorical(data[col]).codes
        
        # Crear combinaciones de variables
        print("\nCreando combinaciones de variables...")
        
        # 1. Combinaciones que ya sabemos que funcionan
        data['seccion_motivo'] = data['seccion'] + '_' + data['motivo']
        data['seccion_motivo_num'] = pd.Categorical(data['seccion_motivo']).codes
        
        # 2. Agregaciones que ya sabemos que funcionan
        mermas_categoria = data.groupby('categoria')['merma_unidad_abs'].transform('mean')
        data['merma_categoria_promedio'] = mermas_categoria
        
        mermas_linea = data.groupby('linea')['merma_unidad_abs'].transform('mean')
        data['merma_linea_promedio'] = mermas_linea
        
        # 3. Nuevas combinaciones con variables temporales
        # Fin de semana por categoría
        data['fin_semana_categoria'] = data['fin_semana'].astype(str) + '_' + data['categoria']
        mermas_fin_semana_cat = data.groupby('fin_semana_categoria')['merma_unidad_abs'].transform('mean')
        data['merma_fin_semana_categoria'] = mermas_fin_semana_cat
        
        # Fin de mes por línea
        data['fin_mes_linea'] = data['fin_mes'].astype(str) + '_' + data['linea']
        mermas_fin_mes_linea = data.groupby('fin_mes_linea')['merma_unidad_abs'].transform('mean')
        data['merma_fin_mes_linea'] = mermas_fin_mes_linea
        
        # Fin de semana por sección
        data['fin_semana_seccion'] = data['fin_semana'].astype(str) + '_' + data['seccion']
        mermas_fin_semana_sec = data.groupby('fin_semana_seccion')['merma_unidad_abs'].transform('mean')
        data['merma_fin_semana_seccion'] = mermas_fin_semana_sec
        
        # Fin de mes por motivo
        data['fin_mes_motivo'] = data['fin_mes'].astype(str) + '_' + data['motivo']
        mermas_fin_mes_mot = data.groupby('fin_mes_motivo')['merma_unidad_abs'].transform('mean')
        data['merma_fin_mes_motivo'] = mermas_fin_mes_mot
        
        return data

    def analizar_correlaciones(self, data):
        """Analizar correlaciones temporales y categóricas"""
        print("\nANÁLISIS DE CORRELACIONES")
        print("=" * 50)
        
        # 0. Todas las correlaciones ordenadas de mayor a menor
        print("\nRanking de Correlaciones (de mayor a menor):")
        print("-" * 80)
        print(f"{'Variable':25} {'Spearman':>10} {'Pearson':>10} {'Tipo':>15}")
        print("-" * 80)
        
        todas_correlaciones = []
        variables_todas = [
            'seccion_motivo_num', 'merma_categoria_promedio', 'merma_linea_promedio',
            'linea_categoria_num', 'linea_motivo_num', 'categoria_motivo_num',
            'merma_seccion_promedio', 'merma_motivo_promedio',
            'merma_linea_categoria_promedio', 'merma_seccion_motivo_promedio',
            'merma_fin_semana_categoria', 'merma_fin_mes_linea',
            'merma_fin_semana_seccion', 'merma_fin_mes_motivo'
        ]
        
        for var in variables_todas:
            try:
                corr_spearman = stats.spearmanr(data[var], data['merma_unidad_abs'])[0]
                corr_pearson = data[var].corr(data['merma_unidad_abs'])
                
                if abs(corr_spearman) >= 0.5 or abs(corr_pearson) >= 0.5:
                    todas_correlaciones.append((var, corr_spearman, corr_pearson))
            except:
                continue
        
        # Ordenar por el valor absoluto de la correlación de Spearman
        todas_correlaciones.sort(key=lambda x: abs(x[1]), reverse=True)
        
        for var, corr_s, corr_p in todas_correlaciones:
            tipo = "Fuerte" if abs(corr_s) > 0.7 or abs(corr_p) > 0.7 else "Moderada"
            print(f"{var:25} {corr_s:10.4f} {corr_p:10.4f} {tipo:>15}")
        
        print("\n" + "=" * 80 + "\n")
        
        # 1. Correlación de Spearman y Pearson para variables originales
        variables_originales = [
            'seccion_motivo_num', 'merma_categoria_promedio', 'merma_linea_promedio',
            'linea_categoria_num', 'linea_motivo_num', 'categoria_motivo_num',
            'merma_seccion_promedio', 'merma_motivo_promedio',
            'merma_linea_categoria_promedio', 'merma_seccion_motivo_promedio'
        ]
        
        print("\nCorrelaciones entre Variables Clave:")
        print("-" * 80)
        print(f"{'Variable':25} {'Spearman':>10} {'Pearson':>10} {'Tipo':>15}")
        print("-" * 80)
        
        correlaciones_originales = []
        for var in variables_originales:
            try:
                corr_spearman = stats.spearmanr(data[var], data['merma_unidad_abs'])[0]
                corr_pearson = data[var].corr(data['merma_unidad_abs'])
                
                if abs(corr_spearman) >= 0.5 or abs(corr_pearson) >= 0.5:
                    correlaciones_originales.append((var, corr_spearman, corr_pearson))
                    tipo = "Fuerte" if abs(corr_spearman) > 0.7 or abs(corr_pearson) > 0.7 else "Moderada"
                    print(f"{var:25} {corr_spearman:10.4f} {corr_pearson:10.4f} {tipo:>15}")
            except:
                continue
        
        # 2. Correlación de Spearman y Pearson para variables temporales
        variables_temporales = [
            'merma_fin_semana_categoria', 'merma_fin_mes_linea',
            'merma_fin_semana_seccion', 'merma_fin_mes_motivo'
        ]
        
        print("\nCorrelaciones con Variables Temporales:")
        print("-" * 80)
        print(f"{'Variable':25} {'Spearman':>10} {'Pearson':>10} {'Tipo':>15}")
        print("-" * 80)
        
        correlaciones_temporales = []
        for var in variables_temporales:
            try:
                corr_spearman = stats.spearmanr(data[var], data['merma_unidad_abs'])[0]
                corr_pearson = data[var].corr(data['merma_unidad_abs'])
                
                if abs(corr_spearman) >= 0.5 or abs(corr_pearson) >= 0.5:
                    correlaciones_temporales.append((var, corr_spearman, corr_pearson))
                    tipo = "Fuerte" if abs(corr_spearman) > 0.7 or abs(corr_pearson) > 0.7 else "Moderada"
                    print(f"{var:25} {corr_spearman:10.4f} {corr_pearson:10.4f} {tipo:>15}")
            except:
                continue
        
        # 3. Visualización de correlaciones originales
        for var, corr_s, corr_p in correlaciones_originales:
            # Determinar las variables para el mapa de calor
            if 'seccion_motivo' in var:
                index_var = 'seccion'
                col_var = 'motivo'
            elif 'linea_categoria' in var:
                index_var = 'linea'
                col_var = 'categoria'
            elif 'linea_motivo' in var:
                index_var = 'linea'
                col_var = 'motivo'
            elif 'categoria_motivo' in var:
                index_var = 'categoria'
                col_var = 'motivo'
            else:
                if 'categoria' in var:
                    index_var = 'categoria'
                    col_var = 'motivo'
                elif 'linea' in var:
                    index_var = 'linea'
                    col_var = 'motivo'
                elif 'seccion' in var:
                    index_var = 'seccion'
                    col_var = 'motivo'
                else:
                    continue
            
            # Crear matriz de mermas promedio
            mermas_matrix = data.pivot_table(
                values='merma_unidad_abs',
                index=index_var,
                columns=col_var,
                aggfunc='mean'
            )
            
            # Renombrar las columnas para fin de semana y fin de mes
            if 'fin_semana' in var:
                mermas_matrix.columns = ['Días laborables', 'Fin de semana']
            elif 'fin_mes' in var:
                mermas_matrix.columns = ['Resto del mes', 'Fin de mes']
            
            # Gráfico de calor
            plt.figure(figsize=(15, 10))
            sns.heatmap(mermas_matrix, 
                       annot=True, 
                       fmt='.2f', 
                       cmap='YlOrRd',
                       cbar_kws={'label': 'Merma Promedio'})
            if 'fin_semana' in var and 'categoria' in var:
                plt.title('¿Qué categorías tienen más mermas los fines de semana? (Categoría vs Fin de Semana)')
            elif 'fin_mes' in var and 'linea' in var:
                plt.title('¿Qué líneas tienen más mermas al final del mes? (Línea vs Fin de Mes)')
            elif 'fin_semana' in var and 'seccion' in var:
                plt.title('¿Qué secciones tienen más mermas los fines de semana? (Sección vs Fin de Semana)')
            elif 'seccion_motivo' in var:
                plt.title('¿Qué motivos de merma son más comunes en cada sección? (Sección vs Motivo)')
            elif 'linea_categoria' in var:
                plt.title('¿Qué líneas tienen más mermas con qué categorías? (Línea vs Categoría)')
            elif 'categoria' in var:
                plt.title('¿Qué categorías tienen más mermas en general? (Categoría vs Merma)')
            elif 'linea' in var:
                plt.title('¿Qué líneas tienen más mermas en general? (Línea vs Merma)')
            plt.xlabel(col_var)
            plt.ylabel(index_var)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.show()
            
            # Gráfico de barras para las top 10 combinaciones
            plt.figure(figsize=(15, 8))
            top_combinaciones = data.groupby([index_var, col_var])['merma_unidad_abs'].mean().nlargest(10)
            
            # Renombrar los índices para fin de semana y fin de mes
            if 'fin_semana' in var:
                top_combinaciones.index = pd.MultiIndex.from_tuples(
                    [(idx[0], 'Días laborables' if idx[1] == 0 else 'Fin de semana') 
                     for idx in top_combinaciones.index]
                )
            elif 'fin_mes' in var:
                top_combinaciones.index = pd.MultiIndex.from_tuples(
                    [(idx[0], 'Resto del mes' if idx[1] == 0 else 'Fin de mes') 
                     for idx in top_combinaciones.index]
                )
            
            top_combinaciones.plot(kind='bar')
            if 'fin_semana' in var and 'categoria' in var:
                plt.title('Top 10: Categorías con mayor pérdida en fin de semana (Categoría vs Fin de Semana)')
            elif 'fin_mes' in var and 'linea' in var:
                plt.title('Top 10: Líneas con mayor pérdida al final del mes (Línea vs Fin de Mes)')
            elif 'fin_semana' in var and 'seccion' in var:
                plt.title('Top 10: Secciones con mayor pérdida en fin de semana (Sección vs Fin de Semana)')
            elif 'seccion_motivo' in var:
                plt.title('Top 10: Secciones y sus principales causas de pérdida (Sección vs Motivo)')
            elif 'linea_categoria' in var:
                plt.title('Top 10: Líneas y sus categorías con mayor pérdida (Línea vs Categoría)')
            elif 'categoria' in var:
                plt.title('Top 10: Categorías con mayor pérdida total (Categoría vs Merma)')
            elif 'linea' in var:
                plt.title('Top 10: Líneas con mayor pérdida total (Línea vs Merma)')
            plt.xlabel(f'Combinación {index_var}-{col_var}')
            plt.ylabel('Merma Promedio')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.show()
        
        # 4. Visualización de correlaciones temporales
        for var, corr_s, corr_p in correlaciones_temporales:
            # Determinar las variables para el mapa de calor
            if 'fin_semana' in var:
                if 'categoria' in var:
                    index_var = 'categoria'
                    col_var = 'fin_semana'
                elif 'seccion' in var:
                    index_var = 'seccion'
                    col_var = 'fin_semana'
            elif 'fin_mes' in var:
                if 'linea' in var:
                    index_var = 'linea'
                    col_var = 'fin_mes'
                elif 'motivo' in var:
                    index_var = 'motivo'
                    col_var = 'fin_mes'
            
            # Crear matriz de mermas promedio
            mermas_matrix = data.pivot_table(
                values='merma_unidad_abs',
                index=index_var,
                columns=col_var,
                aggfunc='mean'
            )
            
            # Renombrar las columnas para fin de semana y fin de mes
            if 'fin_semana' in var:
                mermas_matrix.columns = ['Días laborables', 'Fin de semana']
            elif 'fin_mes' in var:
                mermas_matrix.columns = ['Resto del mes', 'Fin de mes']
            
            # Gráfico de calor
            plt.figure(figsize=(15, 10))
            sns.heatmap(mermas_matrix, 
                       annot=True, 
                       fmt='.2f', 
                       cmap='YlOrRd',
                       cbar_kws={'label': 'Merma Promedio'})
            if 'fin_semana' in var and 'categoria' in var:
                plt.title('¿Qué categorías tienen más mermas los fines de semana? (Categoría vs Fin de Semana)')
            elif 'fin_mes' in var and 'linea' in var:
                plt.title('¿Qué líneas tienen más mermas al final del mes? (Línea vs Fin de Mes)')
            elif 'fin_semana' in var and 'seccion' in var:
                plt.title('¿Qué secciones tienen más mermas los fines de semana? (Sección vs Fin de Semana)')
            elif 'seccion_motivo' in var:
                plt.title('¿Qué motivos de merma son más comunes en cada sección? (Sección vs Motivo)')
            elif 'linea_categoria' in var:
                plt.title('¿Qué líneas tienen más mermas con qué categorías? (Línea vs Categoría)')
            elif 'categoria' in var:
                plt.title('¿Qué categorías tienen más mermas en general? (Categoría vs Merma)')
            elif 'linea' in var:
                plt.title('¿Qué líneas tienen más mermas en general? (Línea vs Merma)')
            plt.xlabel(col_var)
            plt.ylabel(index_var)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.show()
            
            # Gráfico de barras para las top 10 combinaciones
            plt.figure(figsize=(15, 8))
            top_combinaciones = data.groupby([index_var, col_var])['merma_unidad_abs'].mean().nlargest(10)
            
            # Renombrar los índices para fin de semana y fin de mes
            if 'fin_semana' in var:
                top_combinaciones.index = pd.MultiIndex.from_tuples(
                    [(idx[0], 'Días laborables' if idx[1] == 0 else 'Fin de semana') 
                     for idx in top_combinaciones.index]
                )
            elif 'fin_mes' in var:
                top_combinaciones.index = pd.MultiIndex.from_tuples(
                    [(idx[0], 'Resto del mes' if idx[1] == 0 else 'Fin de mes') 
                     for idx in top_combinaciones.index]
                )
            
            top_combinaciones.plot(kind='bar')
            if 'fin_semana' in var and 'categoria' in var:
                plt.title('Top 10: Categorías con mayor pérdida en fin de semana (Categoría vs Fin de Semana)')
            elif 'fin_mes' in var and 'linea' in var:
                plt.title('Top 10: Líneas con mayor pérdida al final del mes (Línea vs Fin de Mes)')
            elif 'fin_semana' in var and 'seccion' in var:
                plt.title('Top 10: Secciones con mayor pérdida en fin de semana (Sección vs Fin de Semana)')
            elif 'seccion_motivo' in var:
                plt.title('Top 10: Secciones y sus principales causas de pérdida (Sección vs Motivo)')
            elif 'linea_categoria' in var:
                plt.title('Top 10: Líneas y sus categorías con mayor pérdida (Línea vs Categoría)')
            elif 'categoria' in var:
                plt.title('Top 10: Categorías con mayor pérdida total (Categoría vs Merma)')
            elif 'linea' in var:
                plt.title('Top 10: Líneas con mayor pérdida total (Línea vs Merma)')
            plt.xlabel(f'Combinación {index_var}-{col_var}')
            plt.ylabel('Merma Promedio')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.show()
        
        # 5. Análisis por categorías
        print("\nTop 1 de cada Correlación:")
        print("-" * 80)
        
        # Top 1 de fin de semana vs categoría
        top_fin_semana_cat = data.groupby('categoria')['merma_unidad_abs'].mean().nlargest(1)
        print(f"\nCategoría con mayor merma en fin de semana:")
        print(f"Categoría: {top_fin_semana_cat.index[0]}")
        print(f"Valor: {top_fin_semana_cat.values[0]:.2f}")
        
        # Top 1 de fin de mes vs línea
        top_fin_mes_linea = data.groupby('linea')['merma_unidad_abs'].mean().nlargest(1)
        print(f"\nLínea con mayor merma en fin de mes:")
        print(f"Línea: {top_fin_mes_linea.index[0]}")
        print(f"Valor: {top_fin_mes_linea.values[0]:.2f}")
        
        # Top 1 de fin de semana vs sección
        top_fin_semana_sec = data.groupby('seccion')['merma_unidad_abs'].mean().nlargest(1)
        print(f"\nSección con mayor merma en fin de semana:")
        print(f"Sección: {top_fin_semana_sec.index[0]}")
        print(f"Valor: {top_fin_semana_sec.values[0]:.2f}")
        
        # Top 1 de sección vs motivo
        top_sec_motivo = data.groupby(['seccion', 'motivo'])['merma_unidad_abs'].mean().nlargest(1)
        print(f"\nCombinación Sección-Motivo con mayor merma:")
        print(f"Sección: {top_sec_motivo.index[0][0]}")
        print(f"Motivo: {top_sec_motivo.index[0][1]}")
        print(f"Valor: {top_sec_motivo.values[0]:.2f}")
        
        # Top 1 de línea vs categoría
        top_linea_cat = data.groupby(['linea', 'categoria'])['merma_unidad_abs'].mean().nlargest(1)
        print(f"\nCombinación Línea-Categoría con mayor merma:")
        print(f"Línea: {top_linea_cat.index[0][0]}")
        print(f"Categoría: {top_linea_cat.index[0][1]}")
        print(f"Valor: {top_linea_cat.values[0]:.2f}")
        
        print("\n" + "=" * 80 + "\n")
        
        # 6. Análisis por categorías
        print("\nAnálisis por categorías:")
        print("-" * 40)
        
        print("\nTop 1 de cada categoría:")
        print("-" * 40)
        for col in ['linea', 'categoria', 'seccion', 'motivo']:
            mermas_por_cat = data.groupby(col)['merma_unidad_abs'].agg(['mean', 'std', 'count'])
            top_1 = mermas_por_cat.sort_values('mean', ascending=False).head(1)
            print(f"\n{col.upper()}:")
            print(f"Valor: {top_1.index[0]}")
            print(f"Merma promedio: {top_1['mean'].values[0]:.2f}")
            
            # Gráfico de barras para las categorías con más mermas
            plt.figure(figsize=(12, 6))
            top_cats = mermas_por_cat.nlargest(10, 'mean')
            top_cats['mean'].plot(kind='bar')
            plt.title(f'Top 10 {col} con mayor merma promedio')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.show()
        
        # 7. Análisis temporal
        print("\nAnálisis temporal:")
        print("-" * 40)
        
        # Top 3 días del mes con mayor merma
        print("\nTop 3 días del mes con mayor merma:")
        print("-" * 40)
        mermas_por_dia_mes = data.groupby('dia_mes')['merma_unidad_abs'].mean()
        top_3_dias = mermas_por_dia_mes.nlargest(3)
        for dia, merma in top_3_dias.items():
            print(f"Día {dia}: {merma:.2f}")
        
        # Estación con mayor merma
        print("\nEstación con mayor merma:")
        print("-" * 40)
        estaciones = ['Invierno', 'Primavera', 'Verano', 'Otoño']
        mermas_por_estacion = data.groupby('estacion')['merma_unidad_abs'].mean()
        estacion_max = mermas_por_estacion.idxmax()
        print(f"Estación: {estaciones[estacion_max-1]}")
        print(f"Merma promedio: {mermas_por_estacion.max():.2f}")
        
        # Día de la semana con mayor merma
        print("\nDía de la semana con mayor merma:")
        print("-" * 40)
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        mermas_por_dia = data.groupby('dia_semana')['merma_unidad_abs'].mean()
        dia_max = mermas_por_dia.idxmax()
        print(f"Día: {dias_semana[dia_max]}")
        print(f"Merma promedio: {mermas_por_dia.max():.2f}")
        
        # Análisis de períodos
        print("\nAnálisis de períodos:")
        print("-" * 40)
        
        # Fin de semana vs días laborables
        mermas_fin_semana = data.groupby('fin_semana')['merma_unidad_abs'].mean()
        print("\nFin de semana vs Días laborables:")
        print(f"Días laborables: {mermas_fin_semana[0]:.2f}")
        print(f"Fin de semana: {mermas_fin_semana[1]:.2f}")
        if mermas_fin_semana[1] > mermas_fin_semana[0]:
            print("→ Hay más mermas en fin de semana")
        else:
            print("→ Hay más mermas en días laborables")
        
        # Fin de mes vs resto del mes
        mermas_fin_mes = data.groupby('fin_mes')['merma_unidad_abs'].mean()
        print("\nFin de mes vs Resto del mes:")
        print(f"Resto del mes: {mermas_fin_mes[0]:.2f}")
        print(f"Fin de mes: {mermas_fin_mes[1]:.2f}")
        if mermas_fin_mes[1] > mermas_fin_mes[0]:
            print("→ Hay más mermas en fin de mes")
        else:
            print("→ Hay más mermas en resto del mes")
        
        # Visualizaciones
        # Por día de la semana
        plt.figure(figsize=(12, 6))
        mermas_por_dia.plot(kind='bar')
        plt.title('Mermas por Día de la Semana')
        plt.xlabel('Día de la Semana')
        plt.ylabel('Merma Unidad Promedio')
        plt.xticks(range(7), dias_semana, rotation=45)
        plt.grid(True, alpha=0.3)
        plt.show()
        
        # Por día del mes
        plt.figure(figsize=(15, 6))
        mermas_por_dia_mes.plot(kind='line', marker='o')
        plt.title('Tendencia de Mermas por Día del Mes')
        plt.xlabel('Día del Mes')
        plt.ylabel('Merma Unidad Promedio')
        plt.grid(True, alpha=0.3)
        plt.show()
        
        # Por estación
        plt.figure(figsize=(10, 6))
        mermas_por_estacion.plot(kind='bar')
        plt.title('Mermas por Estación')
        plt.xlabel('Estación')
        plt.ylabel('Merma Unidad Promedio')
        plt.xticks(range(4), estaciones, rotation=45)
        plt.grid(True, alpha=0.3)
        plt.show()
        
        # Comparación fin de semana vs días laborables
        plt.figure(figsize=(8, 6))
        mermas_fin_semana.plot(kind='bar')
        plt.title('Mermas: Fin de Semana vs Días Laborables')
        plt.xlabel('0: Días Laborables, 1: Fin de Semana')
        plt.ylabel('Merma Unidad Promedio')
        plt.grid(True, alpha=0.3)
        plt.show()
        
        # Comparación fin de mes vs resto del mes
        plt.figure(figsize=(8, 6))
        mermas_fin_mes.plot(kind='bar')
        plt.title('Mermas: Fin de Mes vs Resto del Mes')
        plt.xlabel('0: Resto del Mes, 1: Fin de Mes')
        plt.ylabel('Merma Unidad Promedio')
        plt.grid(True, alpha=0.3)
        plt.show()

    def ejecutar_analisis(self):
        """Ejecutar análisis completo"""
        # 1. Cargar datos
        data = self.cargar_datos()
        
        # 2. Preprocesar datos
        data_processed = self.preprocesar_datos(data)
        
        # 3. Analizar correlaciones
        self.analizar_correlaciones(data_processed)

if __name__ == "__main__":
    analisis = AnalisisCorrelacional()
    analisis.ejecutar_analisis() 
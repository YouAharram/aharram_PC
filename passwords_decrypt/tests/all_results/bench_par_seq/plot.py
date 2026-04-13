import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

def main():
    # File CSV (assicurati che i nomi corrispondano a quelli nella tua cartella)
    file_parallel = "risultati_matrix_scaling.csv"
    file_sequential = "risultati_workload_sequential.csv"
    
    if not os.path.exists(file_parallel) or not os.path.exists(file_sequential):
        print("Errore: Impossibile trovare i file CSV.")
        return

    # Caricamento dati
    df_par = pd.read_csv(file_parallel)
    df_seq = pd.read_csv(file_sequential)
    df = pd.concat([df_par, df_seq], ignore_index=True)
    
    # Pulizia etichette: Il test parallelo a 1 core nel tuo CSV è segnato come "static".
    # Lo rinominiamo per distinguerlo graficamente dal vero "static" multicore.
    df.loc[(df['Cores'] == 1) & (df['Scheduling'] == 'static'), 'Scheduling'] = 'parallelo_1_core'
    
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    
    # =========================================================
    # GRAFICO 1: TEMPO vs CARICO
    # =========================================================
    print("Generazione Grafico 1: Tempo vs Carico di Lavoro...")
    plt.figure(figsize=(10, 6))
    
    # Selezioniamo solo il Sequenziale Puro e le versioni Parallele con i core massimi,
    # rimuovendo la linea del parallelo_1_core
    max_cores = df['Cores'].max()
    df_plot1 = df[
        (df['Scheduling'] == 'sequential') | 
        (df['Cores'] == max_cores)
    ].copy()
    
    # Creiamo etichette eleganti per la legenda
    def format_label(row):
        if row['Scheduling'] == 'sequential': return 'Sequenziale Puro'
        if row['Scheduling'] == 'static': return f'Parallelo ({row["Cores"]} Core) - Static'
        if row['Scheduling'] == 'dynamic': return f'Parallelo ({row["Cores"]} Core) - Dynamic'
        return row['Scheduling']
        
    df_plot1['Configurazione'] = df_plot1.apply(format_label, axis=1)

    sns.lineplot(
        data=df_plot1, 
        x='Anni_Ricerca', 
        y='Tempo_s', 
        hue='Configurazione', 
        style='Configurazione',
        markers=['o', '^', 'D'], # Ridotto a 3 marker
        dashes=False,
        linewidth=2.5,
        palette=["#2c3e50", "#3498db", "#2ecc71"] # Ridotto a 3 colori
    )
    
    plt.title('Scalabilità del Carico: Tempo vs Spazio di Ricerca', pad=15, fontweight='bold')
    plt.xlabel('Spazio di Ricerca (Anni)')
    plt.ylabel('Tempo di Esecuzione (Secondi)')
    
    #plt.xscale('log', base=2)
    #plt.yscale('log', base=10)
    plt.xticks(df['Anni_Ricerca'].unique(), df['Anni_Ricerca'].unique())
    
    plt.tight_layout()
    plt.savefig("plot_tempo_vs_carico.png", dpi=300)
    plt.close()

    # =========================================================
    # GRAFICO 2: SPEEDUP vs CORES (Sul carico massimo)
    # =========================================================
    print("Generazione Grafico 2: Speedup vs Cores...")
    
    # Usiamo il carico di 64 anni per calcolare lo speedup
    max_workload = 64
    df_max_workload = df[df['Anni_Ricerca'] == max_workload].copy()
    
    # Estraiamo il tempo sequenziale puro per calcolare la frazione
    tempo_seq = df_max_workload[df_max_workload['Scheduling'] == 'sequential']['Tempo_s'].values[0]
    
    # Teniamo solo i test paralleli veri (>1 core) e il parallelo 1 core
    df_speedup = df_max_workload[df_max_workload['Scheduling'] != 'sequential'].copy()
    
    # Calcolo: Speedup = T_sequenziale / T_parallelo
    df_speedup['Speedup'] = tempo_seq / df_speedup['Tempo_s']
    
    # Rinominiamo 'parallelo_1_core' di nuovo in 'static' solo per unire la linea nel grafico
    df_speedup.loc[df_speedup['Scheduling'] == 'parallelo_1_core', 'Scheduling'] = 'static'
    
    # Creiamo artificialmente il punto di partenza (1 core, dynamic) per far partire
    # entrambe le linee di scheduling dallo stesso punto nel grafico
    punto_partenza_dynamic = df_speedup[df_speedup['Cores'] == 1].copy()
    punto_partenza_dynamic['Scheduling'] = 'dynamic'
    df_speedup = pd.concat([df_speedup, punto_partenza_dynamic], ignore_index=True)

    plt.figure(figsize=(10, 6))
    
    sns.lineplot(
        data=df_speedup, 
        x='Cores', 
        y='Speedup', 
        hue='Scheduling',
        style='Scheduling',
        markers=['o', 's'],
        dashes=False,
        linewidth=2.5,
        palette=["#3498db", "#2ecc71"]
    )
    
    # Linea dello Speedup Ideale (Lineare)
    cores_list = sorted(df_speedup['Cores'].unique())
    plt.plot(cores_list, cores_list, 'k--', alpha=0.5, label='Speedup Ideale (Lineare)')
    
    plt.title(f'Strong Scaling: Speedup a {max_workload} Anni di Ricerca', pad=15, fontweight='bold')
    plt.xlabel('Numero di Core')
    plt.ylabel('Speedup (Rispetto a Sequenziale Puro)')
    plt.xticks(cores_list)
    
    # Mostriamo la griglia anche sui tick minori
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.legend(title="Strategia di Scheduling")
    
    plt.tight_layout()
    plt.savefig("plot_speedup_vs_cores.png", dpi=300)
    plt.close()

    print("Completato! Controlla la cartella 'results/' per i nuovi grafici.")

if __name__ == "__main__":
    main()

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def main():
    # Sostituisci con i nomi reali dei tuoi file CSV
    # df_ipc = pd.read_csv("risultati_global_exit.csv")
    # df_shared = pd.read_csv("risultati_shared_nothing.csv")
    
    # Per farti testare il codice subito, uso i nomi dei dataframe simulati.
    # Assicurati di caricare i dati corretti qui.
    df_ipc = pd.read_csv("risultati_workload_global.csv")
    df_shared = pd.read_csv("risultati_matrix_scaling.csv")

    # --- GRAFICO 1: Confronto Lineare al massimo carico (256 Anni) ---
    workload = 256
    df_ipc_256 = df_ipc[df_ipc['Anni_Ricerca'] == workload]
    df_sh_256 = df_shared[df_shared['Anni_Ricerca'] == workload]

    plt.figure(figsize=(10, 6))
    plt.plot(df_ipc_256['Cores'], df_ipc_256['Tempo_s'], marker='o', 
             label='Global Exit (IPC Centralizzato)', color='crimson', linewidth=2)
    plt.plot(df_sh_256[df_sh_256['Scheduling'] == 'dynamic']['Cores'], 
             df_sh_256[df_sh_256['Scheduling'] == 'dynamic']['Tempo_s'], marker='s', 
             label='Shared-Nothing (Dynamic)', color='dodgerblue', linewidth=2)
    plt.plot(df_sh_256[df_sh_256['Scheduling'] == 'static']['Cores'], 
             df_sh_256[df_sh_256['Scheduling'] == 'static']['Tempo_s'], marker='^', 
             label='Shared-Nothing (Static)', color='green', linewidth=2, linestyle='--')

    plt.title(f'Confronto Architetturale: Shared-Nothing vs Global Exit\n(Carico Fisso: {workload} Anni)', fontsize=14)
    plt.xlabel('Numero di Core Logici', fontsize=12)
    plt.ylabel('Tempo di Esecuzione (Secondi)', fontsize=12)
    plt.xticks([1, 2, 4, 8, 16, 20])
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig('plot_architetture_linee.png', dpi=300)
    print("Salvato plot_architetture_linee.png")

    # --- GRAFICO 2: Impatto dell'overhead al variare del carico (20 Core) ---
    cores_target = 20
    df_ipc_20 = df_ipc[df_ipc['Cores'] == cores_target].copy()
    df_sh_20 = df_shared[(df_shared['Cores'] == cores_target) & (df_shared['Scheduling'] == 'dynamic')].copy()

    df_bar = pd.merge(df_ipc_20[['Anni_Ricerca', 'Tempo_s']], 
                      df_sh_20[['Anni_Ricerca', 'Tempo_s']], 
                      on='Anni_Ricerca', suffixes=('_IPC', '_Shared'))

    x = np.arange(len(df_bar['Anni_Ricerca']))
    width = 0.35

    plt.figure(figsize=(12, 6))
    plt.bar(x - width/2, df_bar['Tempo_s_IPC'], width, label='Global Exit (Traffico IPC)', color='crimson')
    plt.bar(x + width/2, df_bar['Tempo_s_Shared'], width, label='Shared-Nothing', color='dodgerblue')

    plt.title(f'Impatto dell\'Overhead IPC al variare del Carico ({cores_target} Core)', fontsize=14)
    plt.xlabel('Spazio di Ricerca (Anni)', fontsize=12)
    plt.ylabel('Tempo di Esecuzione (Secondi)', fontsize=12)
    plt.xticks(x, df_bar['Anni_Ricerca'])
    plt.legend(fontsize=11)
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('plot_architetture_barre.png', dpi=300)
    print("Salvato plot_architetture_barre.png")

if __name__ == "__main__":
    main()

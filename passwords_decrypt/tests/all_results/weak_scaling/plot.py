import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

def main():
    # 1. Configurazione del file
    csv_filename = "weak_scaling_data.csv"
    
    if not os.path.exists(csv_filename):
        print(f"Errore: Impossibile trovare '{csv_filename}'.")
        return

    print(f"Caricamento dati da {csv_filename} in corso...")
    df = pd.read_csv(csv_filename)
    
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    cores_list = sorted(df['Cores'].unique())

    # =========================================================
    # GRAFICO 1: EFFICIENZA PERCENTUALE vs CORES
    # =========================================================
    plt.figure(figsize=(10, 6))

    sns.lineplot(
        data=df, 
        x='Cores', 
        y='Efficiency_perc', 
        hue='Scheduling',
        style='Scheduling',
        markers=['o', 's'], 
        dashes=False,
        linewidth=2.5,
        palette=["#e74c3c", "#3498db"] # Rosso e Blu
    )

    # Linea dell'Efficienza Ideale (100% costante)
    plt.axhline(y=100, color='k', linestyle='--', alpha=0.5, label='Efficienza Ideale (100%)')

    plt.title('Weak Scaling: Efficienza del Sistema (Carico: 10 Anni / Core)', pad=15, fontweight='bold')
    plt.xlabel('Numero di Core')
    plt.ylabel('Efficienza (%)')
    plt.xticks(cores_list)
    plt.ylim(0, 110) # Fissiamo l'asse Y da 0 a 110 per chiarezza
    
    plt.grid(True, which="both", ls="-", alpha=0.2)
    
    handles, labels = plt.gca().get_legend_handles_labels()
    plt.legend(handles=handles, labels=labels, title="Strategia", loc='lower left')

    plt.tight_layout()
    output_eff = "plot_weak_scaling_efficienza.png"
    plt.savefig(output_eff, dpi=300)
    plt.close()

    # =========================================================
    # GRAFICO 2: TEMPO DI ESECUZIONE vs CORES
    # =========================================================
    plt.figure(figsize=(10, 6))

    sns.lineplot(
        data=df, 
        x='Cores', 
        y='Time_Seconds', 
        hue='Scheduling',
        style='Scheduling',
        markers=['o', 's'], 
        dashes=False,
        linewidth=2.5,
        palette=["#e74c3c", "#3498db"]
    )

    # Estraiamo il tempo a 1 core (baseline) per disegnare la linea del "Tempo Ideale"
    t1_baseline = df[(df['Cores'] == 1) & (df['Scheduling'] == 'static')]['Time_Seconds'].values[0]
    
    # Nel Weak Scaling ideale, il tempo rimane costante a T1
    plt.axhline(y=t1_baseline, color='k', linestyle='--', alpha=0.5, label='Tempo Ideale (Costante)')

    plt.title('Weak Scaling: Tempo di Esecuzione (Carico: 10 Anni / Core)', pad=15, fontweight='bold')
    plt.xlabel('Numero di Core (e proporzionale aumento del carico)')
    plt.ylabel('Tempo di Esecuzione (Secondi)')
    plt.xticks(cores_list)
    
    # Impostiamo il limite inferiore dell'asse Y a 0 per non distorcere visivamente l'aumento
    plt.ylim(0, df['Time_Seconds'].max() + 0.5)
    
    plt.grid(True, which="both", ls="-", alpha=0.2)
    
    handles, labels = plt.gca().get_legend_handles_labels()
    plt.legend(handles=handles, labels=labels, title="Strategia", loc='upper left')

    plt.tight_layout()
    output_time = "plot_weak_scaling_tempi.png"
    plt.savefig(output_time, dpi=300)
    plt.close()

    print(f"Grafici generati con successo:\n - {output_eff}\n - {output_time}")

if __name__ == "__main__":
    main()

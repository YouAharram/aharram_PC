import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

def main():
    # 1. Configurazione del file di input
    csv_filename = "strong_scaling_data.csv"
    
    # Controllo di sicurezza: verifichiamo che il file esista
    if not os.path.exists(csv_filename):
        print(f"Errore: Impossibile trovare il file '{csv_filename}'.")
        print("Assicurati che si trovi nella stessa cartella di questo script.")
        return

    print(f"Caricamento dati da {csv_filename} in corso...")
    df = pd.read_csv(csv_filename)
    
    # 2. Tempo di riferimento a 1 core (statico) per calcolare la curva ideale
    try:
        t1_baseline = df[(df['Cores'] == 1) & (df['Scheduling'] == 'static')]['Time_Seconds'].values[0]
    except IndexError:
        print("Errore: Impossibile trovare la riga con 1 Core e scheduling 'static' nel CSV per fare da baseline.")
        return

    # 3. Configurazione estetica
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    plt.figure(figsize=(10, 6))

    # 4. Creazione del Lineplot usando Time_Seconds sull'asse Y
    sns.lineplot(
        data=df, 
        x='Cores', 
        y='Time_Seconds', 
        hue='Scheduling',
        style='Scheduling',
        markers=['o', 's'], 
        dashes=False,
        linewidth=2.5,
        palette=["#3498db", "#2ecc71"]
    )

    # 5. Aggiunta della curva del "Tempo Ideale" (T1 / N)
    cores_list = sorted(df['Cores'].unique())
    ideal_times = [t1_baseline / c for c in cores_list]
    plt.plot(cores_list, ideal_times, 'k--', alpha=0.5, label='Tempo Ideale')

    # 6. Rifiniture del grafico
    plt.title('Strong Scaling: Tempo di Esecuzione vs Numero di Core', pad=15, fontweight='bold')
    plt.xlabel('Numero di Core')
    plt.ylabel('Tempo di Esecuzione (Secondi)')
    
    # Mostriamo esattamente i numeri dei core sull'asse X
    plt.xticks(cores_list)
    
    # Mostriamo la griglia anche sui tick minori
    plt.grid(True, which="both", ls="-", alpha=0.2)
    
    # Riordiniamo la legenda e la spostiamo in alto a destra 
    handles, labels = plt.gca().get_legend_handles_labels()
    plt.legend(handles=handles, labels=labels, title="Strategia", loc='upper right')

    # 7. Salvataggio
    plt.tight_layout()
    output_filename = "plot_strong_scaling_tempi.png"
    plt.savefig(output_filename, dpi=300)
    plt.close()

    print(f"Grafico generato con successo: {output_filename}")

if __name__ == "__main__":
    main()

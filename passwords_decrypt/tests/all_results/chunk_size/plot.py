import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

def main():
    # 1. Configurazione del file
    csv_filename = "granularity_data.csv"
    
    if not os.path.exists(csv_filename):
        print(f"Errore: Impossibile trovare '{csv_filename}'.")
        print("Assicurati di aver eseguito prima il benchmark e che la cartella 'results' esista.")
        return

    print(f"Caricamento dati da {csv_filename} in corso...")
    df = pd.read_csv(csv_filename)
    
    # 2. Configurazione estetica
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    plt.figure(figsize=(10, 6))

    # 3. Creazione del Lineplot
    # Usiamo un colore unico acceso (es. rosso/arancio) per evidenziare il collo di bottiglia
    sns.lineplot(
        data=df, 
        x='Chunk_Size', 
        y='Time_Seconds', 
        marker='o', 
        markersize=8,
        linewidth=2.5,
        color="#e74c3c",
        label="Tempo di Esecuzione"
    )

    # 4. Evidenziamo il punto migliore (Best Performance)
    best_row = df.loc[df['Time_Seconds'].idxmin()]
    plt.plot(
        best_row['Chunk_Size'], 
        best_row['Time_Seconds'], 
        marker='*', 
        markersize=15, 
        color='#f1c40f', 
        markeredgecolor='black',
        label=f"Punto Ottimo (Chunk={int(best_row['Chunk_Size'])}, {best_row['Time_Seconds']:.2f}s)"
    )

    # 5. Rifiniture del grafico
    plt.title("Analisi della Granularità (Chunk Size Tuning a 4 Core)", pad=15, fontweight='bold')
    plt.xlabel('Dimensione del Chunk (Anni per pacchetto di lavoro)')
    plt.ylabel('Tempo di Esecuzione (Secondi)')
    
    # Impostiamo l'asse X su scala logaritmica per distribuire meglio i punti (1, 10, 100...)
    plt.xscale('log')
    
    # Forziamo le etichette dell'asse X a mostrare esattamente i tuoi valori invece di notazioni scientifiche
    plt.xticks(df['Chunk_Size'], df['Chunk_Size'])
    
    plt.grid(True, which="both", ls="-", alpha=0.3)
    
    # Aggiungiamo una legenda
    plt.legend(loc='upper left')

    # 6. Salvataggio
    plt.tight_layout()
    output_filename = "plot_granularity.png"
    plt.savefig(output_filename, dpi=300)
    plt.close()

    print(f"Grafico generato con successo: {output_filename}")
    
    # Piccolo report a schermo
    print("\n--- Analisi Empirica ---")
    worst_row = df.loc[df['Time_Seconds'].idxmax()]
    peggioramento = (worst_row['Time_Seconds'] / best_row['Time_Seconds']) * 100 - 100
    print(f"La granularità fine (Chunk={int(best_row['Chunk_Size'])}) è stata la più veloce.")
    print(f"L'uso di chunk monolitici (Chunk={int(worst_row['Chunk_Size'])}) ha causato un peggioramento delle prestazioni del {peggioramento:.1f}%.")

if __name__ == "__main__":
    main()

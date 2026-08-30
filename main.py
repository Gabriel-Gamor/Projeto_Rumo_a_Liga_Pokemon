"""Execute python main.py para abrir o jogo gráfico."""

import sys


def main():
    try:
        import tkinter as tk
        from interface.janela import Aplicacao
    except ImportError as e:
        print('A interface precisa do Tkinter. No Arch Linux: sudo pacman -S tk.\n'
              'No Debian/Ubuntu: sudo apt install python3-tk.\n'
              'No Windows, habilite Tcl/Tk na instalação do Python.\n'+str(e),file=sys.stderr)
        return 1
    try:
        raiz=tk.Tk()
    except tk.TclError as e:
        print('Não foi possível abrir a interface gráfica. Execute em uma sessão de desktop.\n'+str(e),file=sys.stderr)
        return 1
    Aplicacao(raiz)
    raiz.mainloop()
    return 0


if __name__=='__main__':
    raise SystemExit(main())

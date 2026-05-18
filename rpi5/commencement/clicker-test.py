import sys, tty, termios

def main():
    print("Press clicker buttons to test. Ctrl+C to quit.\n")
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            code = ord(ch)
            
            if code == 27:
                seq = sys.stdin.read(2)
                if seq == '[5':
                    sys.stdin.read(1)
                    print("\r>> PREV (Page Up)      ")
                elif seq == '[6':
                    sys.stdin.read(1)
                    print("\r>> NEXT (Page Down)    ")
                elif seq == '[C':
                    print("\r>> RIGHT arrow         ")
                elif seq == '[D':
                    print("\r>> LEFT arrow          ")
                else:
                    print(f"\r>> Unknown: {repr(seq)}")
            elif code == 46:
                print("\r>> HOME button         ")
            elif code == 3:
                break
            else:
                print(f"\r>> Key: {repr(ch)} (code {code})  ")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        print("\nDone.")

if __name__ == "__main__":
    main()
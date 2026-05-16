import tkinter as tk
root = tk.Tk()
root.title("Color Test")
root.geometry("300x200")
root.configure(bg="white")
tk.Label(root, text="This should be BLACK on WHITE", bg="white", fg="black").pack(pady=20)
tk.Label(root, text="This should be WHITE on BLACK", bg="black", fg="white").pack(pady=20)
root.mainloop()

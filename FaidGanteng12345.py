import math


def luas_lingkaran():
    """Menghitung luas lingkaran berdasarkan jari-jari."""
    try:
        r = float(input("Masukkan jari-jari lingkaran: "))
    except ValueError:
        print("Nilai tidak valid, harus berupa angka.")
        return

    if r < 0:
        print("Jari-jari tidak boleh negatif.")
        return

    area = math.pi * r * r
    print(f"Luas lingkaran dengan jari-jari {r} adalah {area:.4f}")


def luas_trapesium():
    """Menghitung luas trapesium (misalnya kebun sawit).

    Rumus: (a + b) * tinggi / 2
    di mana a dan b adalah panjang sisi sejajar.
    """
    try:
        a = float(input("Masukkan panjang sisi sejajar pertama (a): "))
        b = float(input("Masukkan panjang sisi sejajar kedua (b): "))
        t = float(input("Masukkan tinggi trapesium: "))
    except ValueError:
        print("Nilai tidak valid, harus berupa angka.")
        return

    if a < 0 or b < 0 or t < 0:
        print("Panjang sisi dan tinggi tidak boleh negatif.")
        return

    area = (a + b) * t / 2
    print(f"Luas trapesium dengan sisi {a} dan {b} serta tinggi {t} adalah {area:.4f}")


def main():
    """Menu utama untuk memilih perhitungan."""
    print("Pilih operasi:")
    print("1. Luas lingkaran")
    print("2. Luas trapesium (kebun sawit)")

    choice = input("Masukkan pilihan (1/2): ")
    if choice == "1":
        luas_lingkaran()
    elif choice == "2":
        luas_trapesium()
    else:
        print("Pilihan tidak dikenal.")


if __name__ == "__main__":
    main()

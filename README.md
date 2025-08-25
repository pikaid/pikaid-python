<p align="center">
  <img src="https://raw.githubusercontent.com/pikaid/pikaid-python/refs/heads/main/logo.png" alt="pikaid" width="300" />
</p>

# Pikaid (Python)
**Small · Sortable · Secure ID generator**

This is the **official Python implementation.** Fully compliant with v1.0.1.

Pikaid is a **26-character, lowercase Base36 identifier**, composed of:
- **7-character timestamp** (seconds since epoch)
- **19-character cryptographically secure randomness**

It’s a **modern, compact alternative** to UUID and ULID:
- Lexicographically sortable
- Collision-resistant
- Compact binary form (`BINARY(17)`)

![pikaid structure](https://raw.githubusercontent.com/pikaid/pikaid-python/refs/heads/main/structure.png)

---

## 📚 Specifications & Benchmarks
See the full technical specs and benchmarks at
[**pikaid/pikaid-specs**](https://github.com/pikaid/pikaid-specs)

---

## 🙏 Credits

See [CREDITS.md](./CREDITS.md) for authors, contributors and acknowledgments.


---

## 📜 License

Pikaid and this project are released under the [MIT License](./LICENSE).

---

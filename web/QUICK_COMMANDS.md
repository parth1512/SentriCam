# Quick Commands - Copy & Paste

## You're in the `web/` directory? Use these:

### Check Server
```bash
python3 check_server.py
```

### Stop Server
```bash
python3 stop_server.py
```

### Start Server
```bash
python3 start_server.py
```

## You're in the `alpr_project/` directory? Use these:

### Check Server
```bash
./check_server.sh
# or
python3 web/check_server.py
```

### Stop Server
```bash
./stop_server.sh
# or
python3 web/stop_server.py
```

### Start Server
```bash
./start_server.sh
# or
python3 web/start_server.py
```

## Important Notes

1. **Python scripts need `python3` prefix:**
   ```bash
   python3 check_server.py  # ✅ Correct
   check_server.py          # ❌ Wrong (command not found)
   ```

2. **Shell scripts can run directly:**
   ```bash
   ./check_server.sh        # ✅ Works (if executable)
   check_server.sh          # ❌ Wrong (needs ./ prefix)
   ```

3. **From project root, use helper scripts:**
   ```bash
   ./check_server.sh        # ✅ Works from alpr_project/
   ```

## Quick Reference Card

```
Location          Command
─────────────────────────────────────────────────
In web/           python3 check_server.py
In web/           python3 stop_server.py
In web/           python3 start_server.py
─────────────────────────────────────────────────
In alpr_project/  ./check_server.sh
In alpr_project/  ./stop_server.sh
In alpr_project/  ./start_server.sh
─────────────────────────────────────────────────
Anywhere          cd web && python3 check_server.py
```





import traceback
import sys

try:
    with open("server_diagnostic.log", "w", encoding="utf-8") as f:
        f.write("Starting diagnostic...\n")
        try:
            import uvicorn
            f.write("Imported uvicorn\n")
            import s2st.api
            f.write("Imported s2st.api successfully!\n")
        except Exception as e:
            f.write(f"Exception during import: {e}\n")
            traceback.print_exc(file=f)
except Exception as e:
    print("Fatal:", e)

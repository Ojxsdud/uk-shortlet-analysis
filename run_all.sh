#!/usr/bin/env bash
# Full pipeline. Run from the project root with the venv active.
set -euo pipefail
echo "== 1. schema ==";     psql -d shortlet -v ON_ERROR_STOP=1 -q -f sql/01_schema.sql
echo "== 2. load raw ==";   python src/load_raw.py
echo "== 3. transform ==";  psql -d shortlet -v ON_ERROR_STOP=1 -q -f sql/02_transform.sql
echo "== 4. views ==";      psql -d shortlet -v ON_ERROR_STOP=1 -q -f sql/03_views.sql
echo "== 5. indexes ==";    psql -d shortlet -v ON_ERROR_STOP=1 -q -f sql/04_indexes.sql
echo "== 6. analysis ==";   for f in sql/analysis/q*.sql; do
                              echo "   $f"
                              psql -d shortlet -v ON_ERROR_STOP=1 -q --csv -f "$f" \
                                > "outputs/$(basename "$f" .sql).csv"
                            done
echo "== 7. model ==";      python src/model.py
echo "== 8. export ==";     python src/export_for_app.py
echo "ALL OK. Now: streamlit run app/dashboard.py"

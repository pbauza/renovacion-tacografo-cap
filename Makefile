APP_NAME ?= renovaciones_tacografo_cap
ENTRYPOINT ?= main.py

ifeq ($(OS),Windows_NT)
PYTHON ?= py -3.11
DATA_SEP := ;
EXE_PATH := dist\$(APP_NAME)\$(APP_NAME).exe
else
PYTHON ?= python3
DATA_SEP := :
EXE_PATH := dist/$(APP_NAME)/$(APP_NAME).exe
endif

PYINSTALLER_FLAGS := --noconfirm --clean --onedir --name $(APP_NAME)

.PHONY: help build-windows-exe clean-build

help:
	@echo "Targets disponibles:"
	@echo "  make build-windows-exe  # Genera .exe para Windows con PyInstaller"
	@echo "  make clean-build        # Limpia artefactos de build/dist/spec"

build-windows-exe:
ifeq ($(OS),Windows_NT)
	$(MAKE) clean-build
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install pyinstaller
	$(PYTHON) -m PyInstaller $(PYINSTALLER_FLAGS) \
		--add-data "templates$(DATA_SEP)templates" \
		--add-data "static$(DATA_SEP)static" \
		--add-data "config$(DATA_SEP)config" \
		$(ENTRYPOINT)
	@echo "Build completado: $(EXE_PATH)"
else
	@echo "Este target debe ejecutarse en Windows para generar un .exe nativo."
	@exit 1
endif

clean-build:
	$(PYTHON) -c "from pathlib import Path; import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('build','dist')]; [p.unlink() for p in Path('.').glob('*.spec')]"

# Reagent Management System - User Guide

## 🎯 Overview

The Reagent Management System provides complete CRUD (Create, Read, Update, Delete) functionality for both **Antibodies (Reagents)** and **General Reagents** with full unit/vial tracking.

## ✨ Features Implemented

### 1. **Reagents (Antibodies) Management** (`/ui/crud.py`)
- ✅ View list of all antibodies with brand names, fluorochromes, and clones
- ✅ Search and filter antibodies
- ✅ Create new antibodies with full details
- ✅ Edit existing antibody information
- ✅ **DELETE antibodies** (and all associated vials)
- ✅ Manage individual vials (units) for each antibody
- ✅ **DELETE individual vials**
- ✅ Track vial status (Stored, In Use, Empty)
- ✅ Track lot numbers, expiration dates, arrival dates
- ✅ View change history for each vial

### 2. **General Reagents Management** (`/ui/general_reagents.py`)
- ✅ View list of all general reagents (buffers, solutions, consumables)
- ✅ Search and filter general reagents
- ✅ Create new general reagents with full details
- ✅ Edit existing general reagent information
- ✅ **DELETE general reagents** (and all associated units)
- ✅ Manage individual units for each general reagent
- ✅ **DELETE individual units**
- ✅ Track unit status, location, volume
- ✅ Track lot numbers, expiration dates, arrival dates
- ✅ View change history for each unit

### 3. **Brand Display**
- ✅ Brand names properly displayed in all lists
- ✅ Brand selection in forms with readable names
- ✅ Proper brand-reagent relationships

### 4. **Database**
- ✅ Fully initialized with schema
- ✅ 6 brands pre-loaded (BD Biosciences, BioLegend, Thermo Fisher, etc.)
- ✅ 10 fluorochromes pre-loaded (FITC, PE, APC, etc.)
- ✅ Sample data included for testing

## 📋 How to Use

### Accessing the System

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Navigate to reagent management**:
   - For **Antibodies**: Click "Reactivos" in the sidebar
   - For **General Reagents**: Click "Reactivos Generales" in the sidebar

### Managing Antibodies (Reagents)

#### Creating a New Antibody
1. In the left panel, click "➕ Crear Nuevo Anticuerpo"
2. Fill in the required fields:
   - **CD** (required): e.g., "CD3"
   - **Clon**: e.g., "UCHT1"
   - **Catálogo**: e.g., "300459"
   - **Fluorocromo** (required): Select from dropdown
   - **Marca** (required): Select brand from dropdown
   - **Precio referencia**: Price in dollars
3. Click "✓ Crear Anticuerpo"

#### Editing an Antibody
1. Select the antibody from the list
2. In the right panel, click "✏️ Editar Información del Anticuerpo"
3. Modify the fields
4. Click "✓ Guardar Cambios"

#### Deleting an Antibody
1. Select the antibody from the list
2. In the right panel, click "🗑️ Eliminar"
3. Click "Confirmar Eliminación"
   - ⚠️ This will delete the antibody and ALL its vials

#### Managing Vials
1. Select an antibody from the list
2. In the "🧪 Gestión de Viales" section:
   - View all vials in a table
   - Select a vial to edit its details
   - Update volume, dates, status, lot number
   - View change history
   - Delete the vial using "🗑️ Eliminar Vial"

#### Adding New Vials
1. Select an antibody
2. Click "➕ Agregar Nuevo Vial"
3. Fill in:
   - **Volumen inicial (µL)** (required)
   - **Fecha de llegada**
   - **Fecha de vencimiento**
   - **Estado inicial**: Stored / In Use / Empty
   - **Número de lote** (required)
4. Click "✓ Crear Vial"

### Managing General Reagents

#### Creating a New General Reagent
1. In the left panel, click "➕ Crear Nuevo Reactivo General"
2. Fill in the required fields:
   - **Nombre** (required): e.g., "PBS 1X"
   - **Tipo**: e.g., "Buffer", "Solución", "Lisante"
   - **Concentración**: e.g., "1X", "10mM"
   - **Marca** (required): Select from dropdown
   - **Precio referencia**: Price in dollars
   - **Notas**: Additional notes
3. Click "✓ Crear Reactivo General"

#### Editing a General Reagent
1. Select the reagent from the list
2. Click "✏️ Editar Información del Reactivo"
3. Modify the fields
4. Click "✓ Guardar Cambios"

#### Deleting a General Reagent
1. Select the reagent from the list
2. Click "🗑️ Eliminar"
3. Click "Confirmar Eliminación"
   - ⚠️ This will delete the reagent and ALL its units

#### Managing Units
1. Select a general reagent from the list
2. In the "📦 Gestión de Unidades" section:
   - View all units in a table
   - Select a unit to edit its details
   - Update volume, dates, status, location, lot number
   - View change history
   - Delete the unit using "🗑️ Eliminar Unidad"

#### Adding New Units
1. Select a general reagent
2. Click "➕ Agregar Nueva Unidad"
3. Fill in:
   - **Volumen (mL)** (required)
   - **Fecha de llegada**
   - **Fecha de vencimiento**
   - **Estado inicial**: Stored / In Use / Empty
   - **Número de lote** (required)
   - **Ubicación**: e.g., "Refrigerador A, Estante 2"
   - **Notas**: Additional notes
4. Click "✓ Crear Unidad"

## 🗂️ Status Values

Both reagents and general reagents use the same status system:

- **Stored**: Item is in storage, not currently in use
- **In Use**: Item is currently being used in experiments
- **Empty**: Item is finished/depleted

## 📊 Sample Data Included

The system comes pre-loaded with:

### Antibodies
- CD3-FITC (BD Biosciences, clone UCHT1)
- CD4-PE (BioLegend, clone RPA-T4)
- CD8-APC (BD Biosciences, clone SK1)
- CD19-PE-Cy7 (BioLegend, clone HIB19)
- CD45-BV421 (BioLegend, clone HI30)

### General Reagents
- PBS 1X (Thermo Fisher)
- Lysing Buffer 10X (BD Biosciences)
- EDTA 0.5M (Thermo Fisher)
- Fetal Bovine Serum (Thermo Fisher)
- FACS Tubes (BD Biosciences)

## 🔧 Technical Details

### Files Modified
- `/ui/crud.py` - Antibody management with full CRUD
- `/ui/general_reagents.py` - General reagent management with full CRUD
- `/models/loaders.py` - Updated DB path resolution
- `/app.py` - Already integrated (no changes needed)

### Database Tables
- `reagents` - Antibody definitions
- `reagent_units` - Individual vials/units of antibodies
- `general_reagents` - General reagent definitions
- `general_reagent_units` - Individual units of general reagents
- `brands` - Brand/manufacturer information
- `fluorochromes` - Fluorochrome definitions
- `reagent_unit_history` - Change tracking for antibody vials
- `general_reagent_unit_history` - Change tracking for general reagent units

## ✅ Testing

Run the test script to verify everything is working:

```bash
python3 test_reagent_management.py
```

Expected output:
- ✅ 6 brands loaded
- ✅ 10 fluorochromes loaded
- ✅ 5 antibodies with 10 vials
- ✅ 5 general reagents with 9 units
- ✅ Brand names properly displayed

## 🎨 UI Improvements

- Clean two-column layout (list on left, details on right)
- Expandable forms for create/edit operations
- Delete buttons with warnings
- Searchable lists
- Status indicators
- Change history tracking
- Professional styling with consistent spacing

## 🚀 Next Steps

Consider adding:
- Bulk import from CSV/Excel
- Export functionality
- Low stock alerts
- Reorder point management
- Cost tracking and reporting
- Barcode/QR code generation
- Integration with panel builder for automatic inventory deduction

"""
Translation System for Streamflow
Comprehensive bilingual support (English/Spanish)
"""

# Navigation labels
NAV = {
    'en': {
        'operational': '--- OPERATIONAL ---',
        'dashboard': 'Dashboard',
        'panels': 'Panels',
        'panel_builder': 'Panel Builder',
        'clinical': 'Clinical',
        'economic': 'Economic',
        'reagents': 'Reagents',
        'technical': '--- TECHNICAL ---',
        'database': 'Database',
        'advanced_inventory': 'Advanced Inventory',
        'settings': 'Settings'
    },
    'es': {
        'operational': '--- OPERACIONAL ---',
        'dashboard': 'Dashboard',
        'panels': 'Paneles',
        'panel_builder': 'Constructor de Paneles',
        'clinical': 'Clínica',
        'economic': 'Económico',
        'reagents': 'Reactivos',
        'technical': '--- TÉCNICO ---',
        'database': 'Base de Datos',
        'advanced_inventory': 'Inventario Avanzado',
        'settings': 'Configuración'
    }
}

# Dashboard labels
DASHBOARD = {
    'en': {
        'title': 'Flow Cytometry Inventory',
        'search_placeholder': 'Search inventory... cd3, b220, pb, biolegend...',
        'total_antibodies': 'Total Antibodies',
        'in_use': 'In Use',
        'in_use_help': 'Antibody vials currently being used',
        'stored': 'Stored',
        'stored_help': 'Antibody vials not in active use (available)',
        'closed': 'Closed',
        'closed_help': 'Finished or empty vials',
        'general_reagents': 'General Reagents',
        'expired_units': 'expired units found - Click to view',
        'expired_note': 'Note: Expired reagents may still be usable depending on storage conditions',
        'antibody_table': 'Antibody Inventory',
        'general_table': 'General Reagents Inventory'
    },
    'es': {
        'title': 'Inventario de Citometría',
        'search_placeholder': 'Buscar en inventario... cd3, b220, pb, biolegend...',
        'total_antibodies': 'Anticuerpos Totales',
        'in_use': 'En Uso',
        'in_use_help': 'Viales de anticuerpos actualmente en uso',
        'stored': 'Almacenados',
        'stored_help': 'Viales de anticuerpos no en uso activo (disponibles)',
        'closed': 'Cerrados',
        'closed_help': 'Viales terminados o vacíos',
        'general_reagents': 'Reactivos Generales',
        'expired_units': 'unidades vencidas encontradas - Clic para ver',
        'expired_note': 'Nota: Los reactivos vencidos pueden seguir siendo utilizables según las condiciones de almacenamiento',
        'antibody_table': 'Inventario de Anticuerpos',
        'general_table': 'Inventario de Reactivos Generales'
    }
}

# Clinical section labels
CLINICAL = {
    'en': {
        'title': 'Clinical - Oncohematology',
        'dashboard_tab': 'Dashboard',
        'patients_tab': 'Patients',
        'cases_tab': 'Cases',
        'active_patients': 'Active Patients',
        'active_cases': 'Active Cases',
        'completed_month': 'Completed (Month)',
        'recent_cases': 'Recent Cases',
        'patient_registry': 'Patient Registry',
        'case_management': 'Case Management',
        'medical_record_number': 'Medical Record Number',
        'initials': 'Initials',
        'date_of_birth': 'Date of Birth',
        'age': 'Age',
        'sex': 'Sex',
        'referring_physician': 'Referring Physician',
        'referring_institution': 'Referring Institution',
        'notes': 'Notes',
        'register_patient': 'Register Patient',
        'create_case': 'Create Case',
        'case_number': 'Case Number',
        'clinical_suspicion': 'Clinical Suspicion',
        'sample_date': 'Sample Date',
        'sample_type': 'Sample Type',
        'priority': 'Priority',
        'status': 'Status',
        'select_patient': 'Select a patient to view details',
        'select_case': 'Select a case to view details'
    },
    'es': {
        'title': 'Clínica - Oncohematología',
        'dashboard_tab': 'Dashboard',
        'patients_tab': 'Pacientes',
        'cases_tab': 'Casos',
        'active_patients': 'Pacientes Activos',
        'active_cases': 'Casos Activos',
        'completed_month': 'Completados (Mes)',
        'recent_cases': 'Casos Recientes',
        'patient_registry': 'Registro de Pacientes',
        'case_management': 'Gestión de Casos',
        'medical_record_number': 'Número de Historia Clínica',
        'initials': 'Iniciales',
        'date_of_birth': 'Fecha de Nacimiento',
        'age': 'Edad',
        'sex': 'Sexo',
        'referring_physician': 'Médico Remitente',
        'referring_institution': 'Institución Remitente',
        'notes': 'Notas',
        'register_patient': 'Registrar Paciente',
        'create_case': 'Crear Caso',
        'case_number': 'Número de Caso',
        'clinical_suspicion': 'Sospecha Clínica',
        'sample_date': 'Fecha de Muestra',
        'sample_type': 'Tipo de Muestra',
        'priority': 'Prioridad',
        'status': 'Estado',
        'select_patient': 'Seleccione un paciente para ver detalles',
        'select_case': 'Seleccione un caso para ver detalles'
    }
}

# Panels section labels
PANELS = {
    'en': {
        'title': 'Panels',
        'search': 'Search panels',
        'panel_info': 'Panel Information',
        'name': 'Name',
        'description': 'Description',
        'sample_type': 'Sample Type',
        'sample_volume': 'Sample Volume',
        'prewashed_sample': 'Pre-washed Sample',
        'washed_sample': 'Washed Sample',
        'created': 'Created',
        'clinical_area': 'Clinical Area',
        'disease_category': 'Disease Category',
        'clinical_indication': 'Clinical Indication',
        'estimated_cost': 'Est. Cost/Test',
        'panel_composition': 'Panel Composition',
        'version_history': 'Version History',
        'status_history': 'Status History',
        'protocols': 'Protocols',
        'protocols_readonly': 'Protocols (read-only)',
        'protocols_edit_note': 'Protocols can only be edited in Panel Builder to maintain single source of truth',
        'acquisition': 'Acquisition',
        'compensation': 'Compensation',
        'analysis': 'Analysis',
        'status': 'Status',
        'version': 'Version',
        'edit': 'Edit',
        'modify': 'Modify',
        'delete': 'Delete',
        'save_changes': 'Save Changes',
        'cancel': 'Cancel',
        'select_panel': 'Select a panel to view details',
        'no_panels': 'No panels found. Create one in Panel Builder.',
        'no_reagents': 'This panel has no reagents assigned.',
        'cost_calculated': 'Calculated from current cheapest stock. Cost updates when reagent prices change.',
        'cost_complete': '[Complete]',
        'cost_incomplete': '[Incomplete]',
        'cost_error': 'Could not calculate cost',
        'estimated_cost_label': 'Estimated Cost',
        'per_test': 'per test',
        'current_reagents': 'Current Reagents',
        'remove_selected': 'Remove Selected Reagents',
        'version_management': 'Version & Status Management',
        'current_version': 'Current Version',
        'version_update': 'Version Update',
        'keep_current': 'Keep current',
        'patch_version': 'Patch (0.0.X) - Bug fixes',
        'minor_version': 'Minor (0.X.0) - New features',
        'major_version': 'Major (X.0.0) - Breaking changes',
        'version_notes': 'Version Notes',
        'version_notes_placeholder': 'Describe what changed in this version...',
        'current_status': 'Current Status',
        'status_reason': 'Reason for status change',
        'status_reason_placeholder': 'Why is the status changing?',
        'from': 'From',
        'versions': 'versions',
        'changes': 'changes'
    },
    'es': {
        'title': 'Paneles',
        'search': 'Buscar paneles',
        'panel_info': 'Información del Panel',
        'name': 'Nombre',
        'description': 'Descripción',
        'sample_type': 'Tipo de Muestra',
        'sample_volume': 'Volumen de Muestra',
        'prewashed_sample': 'Muestra Pre-lavada',
        'washed_sample': 'Muestra Lavada',
        'created': 'Creado',
        'clinical_area': 'Área Clínica',
        'disease_category': 'Categoría de Enfermedad',
        'clinical_indication': 'Indicación Clínica',
        'estimated_cost': 'Costo Est./Prueba',
        'panel_composition': 'Composición del Panel',
        'version_history': 'Historial de Versiones',
        'status_history': 'Historial de Estado',
        'protocols': 'Protocolos',
        'protocols_readonly': 'Protocolos (solo lectura)',
        'protocols_edit_note': 'Los protocolos solo se pueden editar en el Constructor de Paneles para mantener una única fuente de verdad',
        'acquisition': 'Adquisición',
        'compensation': 'Compensación',
        'analysis': 'Análisis',
        'status': 'Estado',
        'version': 'Versión',
        'edit': 'Editar',
        'modify': 'Modificar',
        'delete': 'Eliminar',
        'save_changes': 'Guardar Cambios',
        'cancel': 'Cancelar',
        'select_panel': 'Seleccione un panel para ver detalles',
        'no_panels': 'No se encontraron paneles. Cree uno en el Constructor de Paneles.',
        'no_reagents': 'Este panel no tiene reactivos asignados.',
        'cost_calculated': 'Calculado del stock más económico actual. El costo se actualiza cuando cambian los precios de los reactivos.',
        'cost_complete': '[Completo]',
        'cost_incomplete': '[Incompleto]',
        'cost_error': 'No se pudo calcular el costo',
        'estimated_cost_label': 'Costo Estimado',
        'per_test': 'por prueba',
        'current_reagents': 'Reactivos Actuales',
        'remove_selected': 'Eliminar Reactivos Seleccionados',
        'version_management': 'Gestión de Versión y Estado',
        'current_version': 'Versión Actual',
        'version_update': 'Actualización de Versión',
        'keep_current': 'Mantener actual',
        'patch_version': 'Parche (0.0.X) - Correcciones de errores',
        'minor_version': 'Menor (0.X.0) - Nuevas características',
        'major_version': 'Mayor (X.0.0) - Cambios importantes',
        'version_notes': 'Notas de Versión',
        'version_notes_placeholder': 'Describa qué cambió en esta versión...',
        'current_status': 'Estado Actual',
        'status_reason': 'Razón del cambio de estado',
        'status_reason_placeholder': '¿Por qué está cambiando el estado?',
        'from': 'Desde',
        'versions': 'versiones',
        'changes': 'cambios'
    }
}

# Settings labels
SETTINGS = {
    'en': {
        'title': 'Settings',
        'clinical_areas': 'Clinical Areas',
        'disease_categories': 'Disease Categories',
        'application': 'Application',
        'language': 'Language / Idioma',
        'database_info': 'Database Information',
        'app_info': 'Application Information'
    },
    'es': {
        'title': 'Configuración',
        'clinical_areas': 'Áreas Clínicas',
        'disease_categories': 'Categorías de Enfermedades',
        'application': 'Aplicación',
        'language': 'Language / Idioma',
        'database_info': 'Información de Base de Datos',
        'app_info': 'Información de la Aplicación'
    }
}

# Common UI labels
COMMON = {
    'en': {
        'yes': 'Yes',
        'no': 'No',
        'save': 'Save',
        'cancel': 'Cancel',
        'add': 'Add',
        'edit': 'Edit',
        'delete': 'Delete',
        'search': 'Search',
        'filter': 'Filter',
        'export': 'Export',
        'import': 'Import',
        'required': 'Required',
        'optional': 'Optional',
        'loading': 'Loading...',
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Information'
    },
    'es': {
        'yes': 'Sí',
        'no': 'No',
        'save': 'Guardar',
        'cancel': 'Cancelar',
        'add': 'Agregar',
        'edit': 'Editar',
        'delete': 'Eliminar',
        'search': 'Buscar',
        'filter': 'Filtrar',
        'export': 'Exportar',
        'import': 'Importar',
        'required': 'Obligatorio',
        'optional': 'Opcional',
        'loading': 'Cargando...',
        'success': 'Éxito',
        'error': 'Error',
        'warning': 'Advertencia',
        'info': 'Información'
    }
}


def get_text(section: str, key: str, language: str = 'en') -> str:
    """
    Get translated text for a given section and key.

    Args:
        section: Section name (NAV, DASHBOARD, CLINICAL, etc.)
        key: Key within the section
        language: 'en' or 'es'

    Returns:
        Translated string or key if not found
    """
    sections = {
        'nav': NAV,
        'dashboard': DASHBOARD,
        'clinical': CLINICAL,
        'panels': PANELS,
        'settings': SETTINGS,
        'common': COMMON
    }

    section_dict = sections.get(section.lower())
    if section_dict and language in section_dict:
        return section_dict[language].get(key, key)
    return key


def get_lang_dict(section: str, language: str = 'en') -> dict:
    """
    Get entire translation dictionary for a section.

    Args:
        section: Section name
        language: 'en' or 'es'

    Returns:
        Dictionary of translations
    """
    sections = {
        'nav': NAV,
        'dashboard': DASHBOARD,
        'clinical': CLINICAL,
        'panels': PANELS,
        'settings': SETTINGS,
        'common': COMMON
    }

    section_dict = sections.get(section.lower())
    if section_dict and language in section_dict:
        return section_dict[language]
    return {}

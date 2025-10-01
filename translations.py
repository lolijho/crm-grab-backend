"""
Backend translation support for CRM Grabovoi Foundation
"""

# Translation dictionaries
TRANSLATIONS = {
    'it': {
        # Authentication messages
        'invalid_credentials': 'Credenziali non valide',
        'email_not_verified': 'Verifica la tua email prima di accedere',
        'login_failed': 'Accesso fallito',
        'user_not_found': 'Utente non trovato',
        'email_already_exists': 'Questo indirizzo email è già registrato',
        'username_already_exists': 'Questo nome utente è già in uso',
        'registration_failed': 'Registrazione fallita',
        'invalid_token': 'Token non valido o scaduto',
        'email_verified': 'Email verificata con successo. Ora puoi accedere.',
        'verification_sent': 'Email di verifica inviata con successo',
        'password_reset_sent': 'Se l\'email esiste, è stato inviato un link per il reset della password',
        'password_reset_success': 'Password reimpostata con successo',
        
        # CRUD operations
        'created_successfully': 'creato con successo',
        'updated_successfully': 'aggiornato con successo', 
        'deleted_successfully': 'eliminato con successo',
        'not_found': 'non trovato',
        
        # Specific entities
        'contact': 'Contatto',
        'product': 'Prodotto',
        'course': 'Corso',
        'order': 'Ordine',
        'tag': 'Tag',
        'user': 'Utente',
        'client': 'Cliente',
        'student': 'Studente',
        
        # Validation errors
        'field_required': 'Questo campo è obbligatorio',
        'invalid_email': 'Indirizzo email non valido',
        'invalid_phone': 'Numero di telefono non valido',
        'invalid_price': 'Prezzo non valido',
        'price_negative': 'Il prezzo non può essere negativo',
        'name_empty': 'Il nome non può essere vuoto',
        'associated_course_not_found': 'Corso associato non trovato',
        'invalid_course_id': 'ID corso non valido',
        
        # Import/Export
        'import_successful': 'Importazione completata con successo',
        'import_failed': 'Importazione fallita',
        'invalid_file_format': 'Formato file non valido',
        'no_data_found': 'Nessun dato trovato',
        
        # General errors
        'internal_error': 'Errore interno del server',
        'unauthorized': 'Non autorizzato',
        'forbidden': 'Accesso negato',
        'bad_request': 'Richiesta non valida',
        'validation_error': 'Errore di validazione',
        
        # Course specific
        'course_auto_creation_restored': 'Ricreazione automatica del corso ripristinata',
        'course_deleted_prevented_recreation': 'Corso eliminato, ricreazione automatica impedita',
        
        # Bulk operations
        'bulk_operation_success': 'Operazione multipla completata con successo',
        'bulk_operation_partial': 'Operazione multipla completata parzialmente',
        'bulk_operation_failed': 'Operazione multipla fallita',
        'items_processed': 'elementi elaborati',
        'items_failed': 'elementi falliti'
    },
    'en': {
        # Authentication messages
        'invalid_credentials': 'Invalid credentials',
        'email_not_verified': 'Please verify your email before logging in',
        'login_failed': 'Login failed',
        'user_not_found': 'User not found',
        'email_already_exists': 'This email address is already registered',
        'username_already_exists': 'This username is already taken',
        'registration_failed': 'Registration failed',
        'invalid_token': 'Invalid or expired token',
        'email_verified': 'Email verified successfully. You can now log in.',
        'verification_sent': 'Verification email sent successfully',
        'password_reset_sent': 'If the email exists, a password reset link has been sent',
        'password_reset_success': 'Password reset successfully',
        
        # CRUD operations
        'created_successfully': 'created successfully',
        'updated_successfully': 'updated successfully',
        'deleted_successfully': 'deleted successfully',
        'not_found': 'not found',
        
        # Specific entities
        'contact': 'Contact',
        'product': 'Product',
        'course': 'Course',
        'order': 'Order',
        'tag': 'Tag',
        'user': 'User',
        'client': 'Client',
        'student': 'Student',
        
        # Validation errors
        'field_required': 'This field is required',
        'invalid_email': 'Invalid email address',
        'invalid_phone': 'Invalid phone number',
        'invalid_price': 'Invalid price',
        'price_negative': 'Price cannot be negative',
        'name_empty': 'Name cannot be empty',
        'associated_course_not_found': 'Associated course not found',
        'invalid_course_id': 'Invalid course ID format',
        
        # Import/Export
        'import_successful': 'Import completed successfully',
        'import_failed': 'Import failed',
        'invalid_file_format': 'Invalid file format',
        'no_data_found': 'No data found',
        
        # General errors
        'internal_error': 'Internal server error',
        'unauthorized': 'Unauthorized',
        'forbidden': 'Access denied',
        'bad_request': 'Bad request',
        'validation_error': 'Validation error',
        
        # Course specific
        'course_auto_creation_restored': 'Course auto-creation restored',
        'course_deleted_prevented_recreation': 'Course deleted, auto-recreation prevented',
        
        # Bulk operations
        'bulk_operation_success': 'Bulk operation completed successfully',
        'bulk_operation_partial': 'Bulk operation completed partially',
        'bulk_operation_failed': 'Bulk operation failed',
        'items_processed': 'items processed',
        'items_failed': 'items failed'
    }
}

def get_translation(key: str, language: str = 'it', **kwargs) -> str:
    """
    Get translated message for given key and language
    
    Args:
        key: Translation key
        language: Language code ('it' or 'en')
        **kwargs: Optional format arguments
    
    Returns:
        Translated string
    """
    if language not in TRANSLATIONS:
        language = 'it'  # Default to Italian
    
    translation = TRANSLATIONS[language].get(key, key)
    
    # Handle string formatting if kwargs provided
    if kwargs:
        try:
            translation = translation.format(**kwargs)
        except (KeyError, ValueError):
            pass  # Return unformatted string if formatting fails
    
    return translation

def get_entity_message(entity: str, operation: str, language: str = 'it') -> str:
    """
    Get standardized entity operation message
    
    Args:
        entity: Entity name key (e.g., 'contact', 'product')
        operation: Operation key (e.g., 'created_successfully', 'deleted_successfully')
        language: Language code
    
    Returns:
        Formatted message like "Contact created successfully" / "Contatto creato con successo"
    """
    entity_name = get_translation(entity, language)
    operation_text = get_translation(operation, language)
    
    return f"{entity_name} {operation_text}"

def get_error_message(error_key: str, language: str = 'it', entity: str = None) -> str:
    """
    Get error message with optional entity context
    
    Args:
        error_key: Error message key
        language: Language code
        entity: Optional entity name for context
    
    Returns:
        Error message
    """
    if entity:
        entity_name = get_translation(entity, language)
        error_msg = get_translation(error_key, language)
        return f"{entity_name} {error_msg}"
    
    return get_translation(error_key, language)
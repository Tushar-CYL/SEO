// Main JavaScript for SEO AI Generator

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // File input validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files[0].name;
            const fileExt = fileName.split('.').pop().toLowerCase();
            
            if (!['csv', 'xls', 'xlsx'].includes(fileExt)) {
                alert('Please upload a valid CSV or Excel file');
                this.value = '';
            }
        });
    });

    // Character counter for meta description input
    const titleInputs = document.querySelectorAll('input[name="title"]');
    titleInputs.forEach(input => {
        input.addEventListener('input', function() {
            if (this.value.length > 60) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid');
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    });
});

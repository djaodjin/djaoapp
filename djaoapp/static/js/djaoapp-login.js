document.addEventListener('DOMContentLoaded', () => {
  const passwordFields = document.querySelectorAll('input[name="password"], ' +
      'input[name="new_password"], input[name="new_password2"]');
  passwordFields.forEach(field => {
    const toggleButton = document.createElement('span');
    toggleButton.innerHTML = '<i class="fa fa-eye"></i>';
    toggleButton.classList.add('password-toggle');
    field.parentElement.style.position = 'relative';
    toggleButton.style.zIndex = 10;
    field.parentElement.appendChild(toggleButton);

    toggleButton.addEventListener('click', () => {
      if (field.type === 'password') {
        field.type = 'text';
        toggleButton.innerHTML = '<i class="fa fa-eye-slash"></i>';
      } else {
        field.type = 'password';
        toggleButton.innerHTML = '<i class="fa fa-eye"></i>';
      }
    });
  });
});

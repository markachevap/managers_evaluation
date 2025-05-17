// Обработчики для всех страниц
$(document).ready(function() {
    // Активация всплывающих подсказок
    $('[data-toggle="tooltip"]').tooltip();

    // Подтверждение удаления
    $('.confirm-delete').click(function() {
        return confirm('Вы уверены, что хотите удалить этот элемент?');
    });
});
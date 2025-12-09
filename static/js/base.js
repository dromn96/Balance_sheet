$(document).ready(function() {
    $('#expensesTable').DataTable({
        "language": {
            "url": "//cdn.datatables.net/plug-ins/1.13.4/i18n/ru.json"
        },
        "pageLength": 25,
        "order": [[2, 'desc']], // Сортировка по стоимости по убыванию
        "columnDefs": [
            {
                "targets": 2, // Колонка стоимости
                "render": function(data, type, row) {
                    if (type === 'sort' || type === 'type') {
                        return data.replace('₽', '').replace(',', '').trim();
                    }
                    return data;
                }
            }
        ]
    });
});


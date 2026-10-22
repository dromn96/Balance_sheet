document.addEventListener('DOMContentLoaded', () => {
  if (!window.gridjs || !window.gridjs.Grid) {
    console.error('Grid.js failed to load; showing the original HTML tables.');
    return;
  }

  const language = {
    search: { placeholder: 'Поиск...' },
    pagination: {
      previous: 'Назад',
      next: 'Вперёд',
      showing: 'Показано',
      results: () => 'записей',
    },
    noRecordsFound: 'Записи не найдены',
  };
  const moneyFormatter = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const formatMoney = (value) => {
    const rawValue = String(value).trim();
    if (!rawValue) return '';

    const amount = Number(rawValue.replace(/[₽\s\u00a0\u202f]/g, '').replace(',', '.'));
    if (!Number.isFinite(amount)) {
      console.error(`Invalid monetary value: ${value}`);
      return rawValue;
    }

    return `${moneyFormatter.format(amount)}\u00a0₽`;
  };
  const tableCellStyles = {
    th: { 'padding-left': '5px', 'padding-right': '0' },
    td: { 'padding-left': '5px', 'padding-right': '0' },
  };

  document.querySelectorAll('#expensesTable').forEach((table) => {
    const headers = Array.from(table.querySelectorAll('thead th'), (cell) => cell.textContent.trim());
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const hasActions = Boolean(table.dataset.editBase && table.dataset.deleteBase);
    const amountColumn = headers.findIndex((header) => /стоимость|сумма дохода/i.test(header));
    const columns = headers.map((name, index) => {
      const column = { name, sort: true };

      if (hasActions && index === 0) {
        column.formatter = (id) => {
          if (!id) return '';
          return gridjs.html(
            `<div class="gridjs-record-actions">
              <a href="${table.dataset.editBase}${id}/edit" title="Редактировать">
                <img src="${table.dataset.editIcon}" alt="Редактировать" class="icon-button">
              </a>
              <a href="#" class="gridjs-delete-icon" data-delete-url="${table.dataset.deleteBase}${id}/delete" title="Удалить">
                <img src="${table.dataset.deleteIcon}" alt="Удалить" class="icon-button">
              </a>
            </div>`
          );
        };
      }

      if (index === amountColumn) {
        column.sort = {
          compare: (left, right) => Number(left) - Number(right),
        };
        column.formatter = formatMoney;
      }

      return column;
    });
    const data = rows.map((row) => Array.from(row.cells, (cell, index) => {
      if (hasActions && index === 0) return row.dataset.id || '';
      return cell.dataset.order || cell.textContent.trim();
    }));

    const mount = document.createElement('div');
    mount.className = 'gridjs-record-table';
    table.before(mount);

    new gridjs.Grid({
      columns,
      data,
      search: true,
      sort: true,
      pagination: { limit: 25 },
      language,
      style: tableCellStyles,
    }).render(mount);
    table.hidden = true;
  });

  document.querySelectorAll('.summary-table').forEach((table) => {
    const headers = Array.from(table.querySelectorAll('thead th'));
    const categoryColumnWidth = headers.length > 1 ? 15 : 100;
    const valueColumnWidth = headers.length > 1
      ? (100 - categoryColumnWidth) / (headers.length - 1)
      : 0;
    const columns = headers.map((cell, index) => {
      const name = cell.textContent.trim();
      return {
        name,
        width: `${index === 0 ? categoryColumnWidth : valueColumnWidth}%`,
        ...(index === 0 ? {} : { formatter: formatMoney }),
      };
    });
    const data = Array.from(table.querySelectorAll('tbody tr, tfoot tr'), (row) =>
      Array.from(row.cells, (cell) => cell.dataset.order || cell.textContent.trim())
    );
    const mount = document.createElement('div');
    mount.className = 'gridjs-summary-table';
    table.before(mount);

    new gridjs.Grid({
      columns,
      data,
      search: false,
      sort: false,
      pagination: false,
      language,
      style: tableCellStyles,
    }).render(mount);
    table.hidden = true;
  });
});

document.addEventListener('click', async (event) => {
  const deleteLink = event.target.closest('.gridjs-delete-icon');
  if (!deleteLink) return;

  event.preventDefault();
  if (!window.confirm('Вы действительно хотите удалить эту запись?')) return;

  const token = document.querySelector('#token input')?.value;
  if (!token) {
    window.alert('Не удалось получить CSRF-токен. Обновите страницу и попробуйте снова.');
    return;
  }

  deleteLink.style.pointerEvents = 'none';
  try {
    const response = await fetch(deleteLink.dataset.deleteUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': token,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      deleteLink.style.pointerEvents = '';
      window.alert('Ошибка при удалении записи');
      return;
    }

    window.location.reload();
  } catch (error) {
    console.error('Не удалось удалить запись:', error);
    deleteLink.style.pointerEvents = '';
    window.alert('Не удалось связаться с сервером. Проверьте соединение и попробуйте снова.');
  }
});

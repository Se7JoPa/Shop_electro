(() => {
  const form = document.getElementById('demo-payment-form');
  if (!form) return;
  const $ = (id) => document.getElementById(id);
  const number = $('card-number'), expiry = $('card-expiry'), cvv = $('card-cvv'), holder = $('card-holder');
  const digits = value => value.replace(/\D/g, '');
  const formatNumber = value => digits(value).slice(0,16).replace(/(\d{4})(?=\d)/g, '$1 ');
  number.addEventListener('input', () => {
    number.value = formatNumber(number.value);
    $('preview-number').textContent = number.value || '••••  ••••  ••••  ••••';
    $('card-brand').textContent = /^4/.test(digits(number.value)) ? 'VISA' : /^5[1-5]/.test(digits(number.value)) ? 'MASTERCARD' : 'BANK CARD';
  });
  expiry.addEventListener('input', () => {
    let value = digits(expiry.value).slice(0,4);
    if (value.length > 2) value = value.slice(0,2) + '/' + value.slice(2);
    expiry.value = value;
    $('preview-expiry').textContent = value || 'ММ/ГГ';
  });
  holder.addEventListener('input', () => {
    holder.value = holder.value.replace(/[^a-zA-Z ]/g, '').toUpperCase().slice(0,40);
    $('preview-name').textContent = holder.value || 'ВАШЕ ИМЯ';
  });
  cvv.addEventListener('input', () => { cvv.value = digits(cvv.value).slice(0,3); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    const card = digits(number.value), exp = expiry.value.split('/'), month = Number(exp[0]);
    const valid = [
      [card.length === 16, 'card-number-error', 'Введите 16 цифр демонстрационной карты.'],
      [exp.length === 2 && month >= 1 && month <= 12 && /^\d{2}$/.test(exp[1]), 'card-expiry-error', 'Укажите срок в формате ММ/ГГ.'],
      [digits(cvv.value).length === 3, 'card-cvv-error', 'Введите 3 цифры CVV.'],
      [holder.value.trim().length >= 3, null, 'Укажите имя владельца латиницей.']
    ];
    ['card-number-error','card-expiry-error','card-cvv-error'].forEach(id => $(id).textContent = '');
    let ok = true;
    valid.forEach(([pass,id,message]) => { if (!pass) { ok = false; if (id) $(id).textContent = message; else window.alert(message); } });
    if (!ok) return;
    // Intentionally keep all card fields in this page only: no request, storage, or logging.
    const receipt = 'DEMO-' + Math.random().toString(36).slice(2,10).toUpperCase();
    $('receipt-id').textContent = receipt;
    form.reset();
    number.value = ''; expiry.value = ''; cvv.value = ''; holder.value = '';
    $('preview-number').textContent = '••••  ••••  ••••  ••••';
    $('preview-expiry').textContent = 'ММ/ГГ'; $('preview-name').textContent = 'ВАШЕ ИМЯ';
    $('card-brand').textContent = 'BANK CARD';
    document.querySelector('.payment-panel').classList.add('is-paid');
    $('payment-result').hidden = false;
  });
  $('reset-payment').addEventListener('click', () => {
    document.querySelector('.payment-panel').classList.remove('is-paid');
    $('payment-result').hidden = true;
  });
})();
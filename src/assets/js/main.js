/* Progressive enhancement only: every page works without this file. */
(() => {
  'use strict';

  const root = document.documentElement;
  const STORAGE_KEY = 'lang';

  const saveLang = (lang) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, lang);
    } catch (error) {
      /* Storage can be blocked; the links still work. */
    }
  };

  const readLang = () => {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (error) {
      return null;
    }
  };

  /* ---- Root language gateway: saved choice, then browser languages, then default. */
  if (root.hasAttribute('data-gateway')) {
    const supported = (root.getAttribute('data-langs') || '').split(',').filter(Boolean);
    const fallback = root.getAttribute('data-default') || supported[0];
    const preferred = navigator.languages && navigator.languages.length
      ? navigator.languages
      : [navigator.language || ''];
    let target = readLang();
    if (!supported.includes(target)) {
      target = preferred
        .map((tag) => String(tag).toLowerCase().split('-')[0])
        .find((code) => supported.includes(code)) || fallback;
    }
    if (target) {
      window.location.replace('/' + target + '/');
    }
  }

  root.classList.add('js');

  /* ---- Remember the language when a language link is followed. */
  document.addEventListener('click', (event) => {
    const link = event.target instanceof Element ? event.target.closest('a[data-lang]') : null;
    if (link) {
      saveLang(link.getAttribute('data-lang'));
    }
  });

  /* ---- Mobile menu. */
  const initMenu = () => {
    const button = document.querySelector('.menu-toggle');
    const nav = document.getElementById('site-nav');
    if (!button || !nav) {
      return;
    }
    const setOpen = (open) => {
      button.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
    };
    button.hidden = false;
    setOpen(false);
    button.addEventListener('click', () => {
      setOpen(button.getAttribute('aria-expanded') !== 'true');
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && button.getAttribute('aria-expanded') === 'true') {
        setOpen(false);
        button.focus();
      }
    });
  };

  /* ---- Contact form. */
  const initForm = () => {
    const form = document.querySelector('form[data-contact]');
    if (!form || typeof window.fetch !== 'function') {
      return;
    }
    const status = form.querySelector('.form-status');
    const submit = form.querySelector('button[type="submit"]');
    const fields = Array.from(form.querySelectorAll('[data-validate]'));
    const messages = form.dataset;

    form.noValidate = true;

    const errorBox = (field) => document.getElementById(field.id + '-error');

    const showError = (field, message) => {
      const box = errorBox(field);
      if (box) {
        box.textContent = message;
        box.hidden = !message;
      }
      if (message) {
        field.setAttribute('aria-invalid', 'true');
      } else {
        field.removeAttribute('aria-invalid');
      }
    };

    const check = (field) => {
      const length = Array.from(field.value.trim()).length;
      /* minLength and maxLength are -1 when the attribute is absent. */
      const min = field.minLength > 0 ? field.minLength : 0;
      const max = field.maxLength > 0 ? field.maxLength : Infinity;
      if (length === 0) {
        return field.required ? field.dataset.msgRequired : '';
      }
      if (length < min) {
        return field.dataset.msgShort;
      }
      if (length > max) {
        return field.dataset.msgLong;
      }
      return '';
    };

    const setStatus = (kind, text, withLink) => {
      status.className = 'form-status' + (kind ? ' is-' + kind : '');
      status.textContent = text;
      if (withLink && messages.altUrl) {
        const link = document.createElement('a');
        link.href = messages.altUrl;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = messages.altLabel || messages.altUrl;
        if (messages.altNote) {
          const note = document.createElement('span');
          note.className = 'visually-hidden';
          note.textContent = ' ' + messages.altNote;
          link.appendChild(note);
        }
        status.appendChild(document.createTextNode(' '));
        status.appendChild(link);
      }
    };

    const validateAll = () => {
      let firstInvalid = null;
      fields.forEach((field) => {
        const message = check(field);
        showError(field, message);
        if (message && !firstInvalid) {
          firstInvalid = field;
        }
      });
      return firstInvalid;
    };

    fields.forEach((field) => {
      field.addEventListener('input', () => {
        if (field.hasAttribute('aria-invalid') && !check(field)) {
          showError(field, '');
        }
      });
    });

    const SERVER_FIELDS = {
      invalid_name: 'name',
      invalid_contact: 'contact',
      invalid_message: 'message'
    };

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (submit.getAttribute('aria-disabled') === 'true') {
        return;
      }
      const firstInvalid = validateAll();
      if (firstInvalid) {
        setStatus('', '');
        firstInvalid.focus();
        return;
      }

      /* aria-disabled, not disabled: a disabled button would lose keyboard focus. */
      submit.setAttribute('aria-disabled', 'true');
      setStatus('pending', messages.msgSending);
      try {
        const response = await window.fetch(form.action, {
          method: 'POST',
          headers: { Accept: 'application/json' },
          body: new URLSearchParams(new FormData(form)),
          credentials: 'same-origin'
        });
        let data = null;
        try {
          data = await response.json();
        } catch (error) {
          data = null;
        }

        if (response.ok && data && data.ok === true) {
          form.reset();
          setStatus('success', messages.msgSuccess);
        } else if (response.status === 429) {
          setStatus('error', messages.msgRate);
        } else if (response.status === 400 && data && SERVER_FIELDS[data.error]) {
          const field = form.elements[SERVER_FIELDS[data.error]];
          setStatus('', '');
          showError(field, messages.msgField);
          field.focus();
        } else {
          setStatus('error', messages.msgError, true);
        }
      } catch (error) {
        setStatus('error', messages.msgError, true);
      } finally {
        submit.removeAttribute('aria-disabled');
      }
    });
  };

  const init = () => {
    initMenu();
    initForm();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

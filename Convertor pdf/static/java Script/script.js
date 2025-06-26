// script.js for PDFPro Toolkit

// Smooth scroll to Tools section
document.addEventListener('DOMContentLoaded', () => {
    const exploreLink = document.querySelector('.cta a[href="#tools"]');
    if (exploreLink) {
      exploreLink.addEventListener('click', e => {
        e.preventDefault();
        const target = document.getElementById('tools');
        if (target) {
          target.scrollIntoView({ behavior: 'smooth' });
        }
      });
    }
  
    // Dropdown hover and click-outside behavior
    const dropdown = document.querySelector('.dropdown');
    const menu = document.querySelector('.dropdown-content');
  
    dropdown.addEventListener('mouseenter', () => {
      menu.style.display = 'block';
    });
    dropdown.addEventListener('mouseleave', () => {
      menu.style.display = 'none';
    });
  
    document.addEventListener('click', e => {
      if (!dropdown.contains(e.target)) {
        menu.style.display = 'none';
      }
    });
  });
  
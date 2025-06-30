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
  document.addEventListener('click', e => {
      if (!dropdown.contains(e.target)) {
        menu.style.display = 'none';
      }
    });

    // 3D tilt effect for tool cards
    document.querySelectorAll('.tool').forEach(card => {
      card.style.transformStyle = 'preserve-3d';
      card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        const rotateX = (-y / rect.height) * 10;
        const rotateY = (x / rect.width) * 10;
        card.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(800px) rotateX(0) rotateY(0)';
      });
    });
  });
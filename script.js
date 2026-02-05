document.addEventListener('DOMContentLoaded', () => {
    // Initialize AOS
    AOS.init({
        duration: 800,
        once: true,
        offset: 100
    });

    // --- Image Slider Logic (Gallery) ---
    const slides = document.querySelectorAll('.slide');
    const nextBtn = document.querySelector('.next-btn');
    const prevBtn = document.querySelector('.prev-btn');
    const dotsContainer = document.querySelector('.slider-dots');
    
    let currentSlide = 0;
    
    // Create dots
    slides.forEach((_, index) => {
        const dot = document.createElement('div');
        dot.classList.add('slider-dot');
        if (index === 0) dot.classList.add('active');
        dot.addEventListener('click', () => goToSlide(index));
        dotsContainer.appendChild(dot);
    });

    const dots = document.querySelectorAll('.slider-dot');

    function goToSlide(n) {
        slides[currentSlide].classList.remove('active');
        dots[currentSlide].classList.remove('active');
        
        currentSlide = (n + slides.length) % slides.length;
        
        slides[currentSlide].classList.add('active');
        dots[currentSlide].classList.add('active');
    }

    if (nextBtn && prevBtn) {
        nextBtn.addEventListener('click', () => goToSlide(currentSlide + 1));
        prevBtn.addEventListener('click', () => goToSlide(currentSlide - 1));
    }

    // --- Comparison Slider Logic (Drag Anywhere) ---
    const comparisonContainers = document.querySelectorAll('.img-comparison-container');

    comparisonContainers.forEach(container => {
        const afterImageWrapper = container.querySelector('.after-image');
        const sliderHandle = container.querySelector('.slider-handle');

        if (afterImageWrapper && sliderHandle) {
            // 1. Create the vertical line dynamically
            const sliderLine = document.createElement('div');
            Object.assign(sliderLine.style, {
                position: 'absolute',
                top: '0',
                bottom: '0',
                width: '2px',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: '40', 
                pointerEvents: 'none', // Allow clicks to pass through to container
                boxShadow: '0 0 5px rgba(0,0,0,0.5)'
            });
            container.appendChild(sliderLine);
            
            // Ensure handle is above everything but lets events bubble if needed
            sliderHandle.style.zIndex = '50';
            sliderHandle.style.pointerEvents = 'none'; // distinct handle clicks not strictly needed if container handles all

            let isDragging = false;

            const moveSlider = (e) => {
                // Prevent calculation if we aren't "active" (though logic below handles this)
                // We actually want moveSlider to run ONCE on click, even if not moving yet.
                
                const clientX = e.touches ? e.touches[0].clientX : e.clientX;
                const rect = container.getBoundingClientRect();
                let x = clientX - rect.left;
                
                // Boundaries
                if (x < 0) x = 0;
                if (x > rect.width) x = rect.width;
                
                const percentage = (x / rect.width) * 100;
                const clipAmount = 100 - percentage;
                
                // Update CSS
                afterImageWrapper.style.clipPath = `inset(0 ${clipAmount}% 0 0)`;
                sliderHandle.style.left = `${percentage}%`;
                sliderLine.style.left = `${percentage}%`;
            };

            const startDrag = (e) => {
                isDragging = true;
                e.preventDefault(); // Stop text selection
                moveSlider(e); // Immediately jump to where the user clicked
            };

            // 2. Attach start listeners to the WHOLE CONTAINER
            container.addEventListener('mousedown', startDrag);
            container.addEventListener('touchstart', startDrag);
            
            // 3. Global Stop Listeners
            window.addEventListener('mouseup', () => isDragging = false);
            window.addEventListener('touchend', () => isDragging = false);

            // 4. Global Move Listeners
            window.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                moveSlider(e);
            });
            window.addEventListener('touchmove', (e) => {
                if (!isDragging) return;
                moveSlider(e);
            });
            
            // Initial State
            afterImageWrapper.style.clipPath = `inset(0 50% 0 0)`;
            sliderHandle.style.left = `50%`;
            sliderLine.style.left = `50%`;
        }
    });

    // --- Dynamic Background Blur ---
    window.addEventListener('scroll', () => {
        const scrollValues = window.scrollY;
        const maxScroll = 600;
        let blurAmount = 0 + (Math.min(scrollValues, maxScroll) / maxScroll) * 20; 
        document.body.style.setProperty('--bg-blur', `${blurAmount}px`);
    });

    // --- Image Cycling for Stacked Cards ---
    const imageLibrary = {
        multi: [
            'assets/real_env/multi_1.png', 
            'assets/real_env/multi_2.png',
            'assets/real_env/multi_3.png',
            'assets/real_env/multi_4.png'
        ],
        occlusion_clutter: [
            'assets/real_env/occlusion_clutter_1.png', 
            'assets/real_env/occlusion_clutter_2.png',
            'assets/real_env/occlusion_clutter_3.png',
            'assets/real_env/occlusion_clutter_4.png',
            'assets/real_env/occlusion_clutter_5.png',
            'assets/real_env/occlusion_clutter_6.png'
        ]
    };

    const stackedCards = document.querySelectorAll('.stacked-card');
    
    stackedCards.forEach(card => {
        const category = card.getAttribute('data-category');
        const images = imageLibrary[category];
        const wrapper = card.querySelector('.stack-front-wrapper');
        
        if (images && wrapper) {
            let currentIndex = 0;
            
            setInterval(() => {
                const nextIndex = (currentIndex + 1) % images.length;
                const nextImageSrc = images[nextIndex];
                
                const currentImg = wrapper.querySelector('img:last-of-type'); 
                
                const newImg = document.createElement('img');
                newImg.src = nextImageSrc;
                newImg.className = 'stack-img slide-in-from-right animating';
                wrapper.appendChild(newImg);
                
                void newImg.offsetWidth;
                
                requestAnimationFrame(() => {
                    newImg.style.transform = 'translateX(0)';
                    
                    if (currentImg) {
                        currentImg.classList.add('animating');
                        currentImg.classList.add('slide-out-to-left');
                    }
                });
                
                setTimeout(() => {
                    if (currentImg && currentImg.parentNode === wrapper) {
                        wrapper.removeChild(currentImg);
                    }
                    newImg.classList.remove('slide-in-from-right', 'animating');
                    newImg.style.transform = ''; 
                }, 800);
                
                currentIndex = nextIndex;
                
            }, 3000); 
        }
    });

    // --- Image Modal Logic ---
    const modal = document.createElement('div');
    modal.classList.add('modal');
    modal.innerHTML = `
        <div class="close-modal"><i class="fa-solid fa-xmark"></i></div>
        <img class="modal-content" src="" alt="Zoomed Image">
    `;
    document.body.appendChild(modal);

    const modalImg = modal.querySelector('.modal-content');
    const closeModal = modal.querySelector('.close-modal');

    const openModal = (src) => {
        modalImg.src = src;
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    };

    document.querySelectorAll('.gallery-img, .dist-img').forEach(img => {
        img.addEventListener('click', () => openModal(img.src));
    });
    
    const hideModal = () => {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    };

    closeModal.addEventListener('click', hideModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) hideModal();
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            hideModal();
        }
    });

});

function copyCitation() {
    const codeBlock = document.getElementById('bibtex');
    const text = codeBlock.innerText;
    
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector('.copy-btn');
        const originalText = btn.innerHTML;
        
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
        setTimeout(() => {
            btn.innerHTML = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}
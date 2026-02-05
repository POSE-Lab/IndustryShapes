document.addEventListener('DOMContentLoaded', () => {
    // Initialize AOS
    AOS.init({
        duration: 800,
        once: true,
        offset: 100
    });

    // --- Image Slider Logic ---
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

    // Auto Advance (Optional)
    setInterval(() => {
        // goToSlide(currentSlide + 1); 
    }, 5000);


    // --- Comparison Slider Logic ---
    const comparisonContainer = document.querySelector('.img-comparison-container');
    const afterImageWrapper = document.querySelector('.after-image');
    const sliderHandle = document.querySelector('.slider-handle');

    if (comparisonContainer && afterImageWrapper && sliderHandle) {
        let isDragging = false;

        const moveSlider = (e) => {
            // Get proper x coordinate depending on event type (mouse or touch)
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            
            const rect = comparisonContainer.getBoundingClientRect();
            let x = clientX - rect.left;
            
            // Constrain x within container bounds
            if (x < 0) x = 0;
            if (x > rect.width) x = rect.width;
            
            const percentage = (x / rect.width) * 100;
            
            // Use clip-path to reveal/hide image without squashing
            // We want to show the left X% of the image.
            // So we clip the RIGHT side.
            // inset(top right bottom left) -> inset(0 (100-P)% 0 0)
            const clipAmount = 100 - percentage;
            afterImageWrapper.style.clipPath = `inset(0 ${clipAmount}% 0 0)`;
            
            sliderHandle.style.left = `${percentage}%`;
        };

        sliderHandle.addEventListener('mousedown', () => isDragging = true);
        sliderHandle.addEventListener('touchstart', () => isDragging = true);

        window.addEventListener('mouseup', () => isDragging = false);
        window.addEventListener('touchend', () => isDragging = false);

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            moveSlider(e);
        });
        
        window.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            moveSlider(e);
        });
        
        // Initial State (50%)
        afterImageWrapper.style.clipPath = `inset(0 50% 0 0)`;
        sliderHandle.style.left = `50%`;

        comparisonContainer.addEventListener('mousedown', (e) => {
             moveSlider(e);
             isDragging = true;
        });
    }

    // --- Dynamic Background Blur ---
    const bgElement = document.querySelector('body::before'); 
    // Wait, we can't select pseudo-elements. 
    // We switched to using body::before, so we actually need to change the CSS variable or class.
    // Or we should have used a real element.
    // I previously tried to change index.html to add #dynamic-bg but reverted it?
    // Let's check style.css again. I DID edit style.css to use body::before.
    // So JS cannot control it directly easily unless we use CSS variables.
    
    // Let's attach a variable to body
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
                
                // Get current image (the one visible)
                const currentImg = wrapper.querySelector('img:last-of-type'); 
                // Note: if animation is fast, there might be multiple. 
                // But usually we clean up. safely: selector :not(.slide-out-to-left)
                
                // Create New Image
                const newImg = document.createElement('img');
                newImg.src = nextImageSrc;
                newImg.className = 'stack-img slide-in-from-right animating';
                wrapper.appendChild(newImg);
                
                // Force Reflow to ensure start position is applied
                void newImg.offsetWidth;
                
                // Start Animation
                requestAnimationFrame(() => {
                    // Move New Image In
                    newImg.style.transform = 'translateX(0)';
                    
                    // Move Old Image Out
                    if (currentImg) {
                        currentImg.classList.add('animating');
                        currentImg.classList.add('slide-out-to-left');
                    }
                });
                
                // Clean up after animation (0.8s matches CSS)
                setTimeout(() => {
                    if (currentImg && currentImg.parentNode === wrapper) {
                        wrapper.removeChild(currentImg);
                    }
                    newImg.classList.remove('slide-in-from-right', 'animating');
                    newImg.style.transform = ''; // Clear inline transform
                }, 800);
                
                currentIndex = nextIndex;
                
            }, 3000); // Cycle every 3 seconds
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

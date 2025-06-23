let currentSlide = 0;
const slider = document.getElementById('policySlider');
const slides = slider.children;
const totalSlides = slides.length;
const slidesToShow = window.innerWidth < 768 ? 1 : window.innerWidth < 1024 ? 2 : 4;

function updateSlider() {
    const offset = currentSlide * -100;
    slider.style.transform = `translateX(${offset}%)`;
}

function slideNext() {
    const maxSlide = Math.max(0, Math.ceil(totalSlides / slidesToShow) - 1);
    if (currentSlide < maxSlide) {
        currentSlide++;
        updateSlider();
    }
}

function slidePrev() {
    if (currentSlide > 0) {
        currentSlide--;
        updateSlider();
    }
}

// 반응형 처리
window.addEventListener('resize', () => {
    const newSlidesToShow = window.innerWidth < 768 ? 1 : window.innerWidth < 1024 ? 2 : 4;
    if (newSlidesToShow !== slidesToShow) {
        currentSlide = 0;
        updateSlider();
    }
});

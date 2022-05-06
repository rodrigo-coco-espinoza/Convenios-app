function changeActive(id){
  const sideMenu = document.querySelectorAll("#sidebarMenu a");
  sideMenu.forEach(option => {
    option.classList.remove('active');
  });
  document.querySelector(id).classList.add('active');
}

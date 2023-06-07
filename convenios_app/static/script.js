function changeActive(id){
  const sideMenu = document.querySelectorAll("#sidebarMenu a");
  sideMenu.forEach(option => {
    option.classList.remove('active');
  });
  document.querySelector(id).classList.add('active');
}

function changeEtiquetaSFTP(selected){
  // Si se abre el mes
  if (selected.getAttribute("aria-expanded") === "true") {

    // Cerrar todas las pestañas y volver al color original
    const etiquetas = document.querySelectorAll(".etiqueta-mes");
    etiquetas.forEach(etiqueta => {
      etiqueta.parentNode.classList.remove("bg-primary");
      etiqueta.parentNode.classList.add("bg-dark");

      etiqueta.classList.add("collapsed");
      etiqueta.setAttribute("aria-expanded", "false");
      
      const id_tabla = etiqueta.getAttribute("aria-controls");
      $(`#${id_tabla}`).removeClass("show"); 
      
    });

    // Cambiar color y abrir mes seleccinado
    $(`#${selected.id}`).parent().removeClass("bg-dark");
    $(`#${selected.id}`).parent().addClass("bg-primary");
    $(`#${selected.id}`).removeClass("collapsed");
    $(`#${selected.id}`).attr("aria-expanded", "true");


  // Si se cierra el mes
  } else {
    // Volver todos los meses al original
    const etiquetas = document.querySelectorAll(".etiqueta-mes");
    etiquetas.forEach(etiqueta => {
      etiqueta.parentNode.classList.remove("bg-primary");
      etiqueta.parentNode.classList.add("bg-dark");

      etiqueta.classList.add("collapsed");
      etiqueta.setAttribute("aria-expanded", "false");
      
      const id_tabla = etiqueta.getAttribute("aria-controls");
      $(`#${id_tabla}`).removeClass("show");     
    });
  }
}

function changeEtiquetaAno(selected){
  // Cerrar todos los meses
  const etiquetas = document.querySelectorAll(".etiqueta-mes");
  etiquetas.forEach(etiqueta => {
    etiqueta.parentNode.classList.remove("bg-primary");
    etiqueta.parentNode.classList.add("bg-dark");

    etiqueta.classList.add("collapsed");
    etiqueta.setAttribute("aria-expanded", "false");
    
    const id_tabla = etiqueta.getAttribute("aria-controls");
    $(`#${id_tabla}`).removeClass("show");     
  });

  // Cerrar todas las insittucones
  const etiquetas_institucones = document.querySelectorAll(".etiqueta-institucion");
  etiquetas_institucones.forEach(etiqueta => {
    etiqueta.classList.add("collapsed");
    etiqueta.setAttribute("aria-expanded", "false");
    // Cambiar color de la institución a gris
    etiqueta.firstChild.classList.remove("text-dark");
    etiqueta.firstChild.classList.add("text-secondary");

    
    const id_tabla = etiqueta.getAttribute("aria-controls");
    $(`#${id_tabla}`).removeClass("show");     
  });

  // Si se abre el año
  if (selected.getAttribute("aria-expanded") === "true") {
    // Cerrar todas las pestañas
    const etiquetas = document.querySelectorAll(".etiqueta-ano");
    etiquetas.forEach( etiqueta => {      
      etiqueta.classList.add("collapsed");
      etiqueta.setAttribute("aria-expanded", "false");
      
      const id_tabla = etiqueta.getAttribute("aria-controls");
      $(`#${id_tabla}`).removeClass("show"); 
      
      });
  } else {

  }
}


function changeEtiquetaInstitucion(selected){
  // Cerrar todas las instituciones
  const etiquetas = document.querySelectorAll(".etiqueta-institucion");
  etiquetas.forEach(etiqueta => {
    etiqueta.classList.add("collapsed");
    etiqueta.setAttribute("aria-expanded", "false");

    // Cambiar color de la institución a gris
    etiqueta.firstChild.classList.remove("text-dark");
    etiqueta.firstChild.classList.add("text-secondary");
    
    const id_tabla = etiqueta.getAttribute("aria-controls");
    $(`#${id_tabla}`).removeClass("show");
    
    
  });
  // Cambiar color de la institución seleccionada
  selected.classList.remove("text-secondary");
  selected.classList.add("text-dark");
}
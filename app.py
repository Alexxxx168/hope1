import io
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle 
from reportlab.lib import colors

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///colegio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'cambia-esta-clave-por-una-clave-privada-y-segura'

db = SQLAlchemy(app)

ANIO_ESCOLAR_ACTUAL = 2026

# -----------------------------------------------------------------------------
# MATERIAS POR NIVEL
# Ajusta los nombres de grados para que coincidan EXACTAMENTE con los del HTML.
# -----------------------------------------------------------------------------
MATERIAS_PREPRIMARIA = [
    'Destrezas de Aprendizaje Matemático',
    'Destrezas de Comunicación y Lenguaje',
    'Educación para la Ciencia y la Ciudadanía',
    'Educación Artística: Educación Musical y Artes Visuales',
    'Educación Física',
    'Inglés',
    'Educación Cristiana',
]

MATERIAS_PRIMARIA_BAJA = [
    'Comunicación y Lenguaje L1 (Idioma Materno)',
    'Comunicación y Lenguaje L2 (Segundo Idioma)',
    'Comunicación y Lenguaje L3 (Tercer Idioma)',
    'Matemáticas',
    'Medio Social y Natural',
    'Ciencias Naturales y Tecnología',
    'Ciencias Sociales',
    'Expresión Artística',
    'Educación Física',
    'Formación Ciudadana',
    'Educación Cristiana',
]

MATERIAS_PRIMARIA_ALTA = [
    'Comunicación y Lenguaje L1 (Idioma Materno)',
    'Comunicación y Lenguaje L2 (Segundo Idioma)',
    'Comunicación y Lenguaje L3 (Tercer Idioma)',
    'Matemáticas',
    'Medio Social y Natural',
    'Ciencias Naturales y Tecnología',
    'Ciencias Sociales',
    'Expresión Artística',
    'Educación Física',
    'Formación Ciudadana',
    'Productividad y Desarrollo',
    'Educación Cristiana',
]


def obtener_materias_por_grado(grado):
    if grado in ['Pre-kinder', 'Kínder', 'Preparatoria', 'Preprimaria']:
        return MATERIAS_PREPRIMARIA
    if grado in ['1ro Primaria', '2do Primaria', '3ro Primaria']:
        return MATERIAS_PRIMARIA_BAJA
    return MATERIAS_PRIMARIA_ALTA

# Lista oficial de grados del colegio
GRADOS_OFICIALES = [
    'Pre-kínder',
    'Kínder',
    'Preparatoria',
    '1ro Primaria',
    '2do Primaria',
    '3ro Primaria',
    '4to Primaria',
    '5to Primaria',
    '6to Primaria'
]

# -----------------------------------------------------------------------------
# MODELOS
# -----------------------------------------------------------------------------
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # admin o maestro
    grado_asignado = db.Column(db.String(50), nullable=True)


class Estudiante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    grado = db.Column(db.String(50), nullable=False)
    estado_pago = db.Column(db.String(20), default='Al día', nullable=False)
    estado_academico = db.Column(db.String(20), default='Activo', nullable=False)
    notas = db.relationship(
        'Nota', backref='estudiante', lazy=True,
        cascade='all, delete-orphan'
    )
    pagos = db.relationship(
        'Pago', backref='estudiante', lazy=True,
        cascade='all, delete-orphan'
    )


class Nota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    materia = db.Column(db.String(120), nullable=False)
    bimestre_1 = db.Column(db.Float, default=0.0, nullable=False)
    bimestre_2 = db.Column(db.Float, default=0.0, nullable=False)
    bimestre_3 = db.Column(db.Float, default=0.0, nullable=False)
    bimestre_4 = db.Column(db.Float, default=0.0, nullable=False)
    promedio_final = db.Column(db.Float, default=0.0, nullable=False)
    anio_escolar = db.Column(db.Integer, default=ANIO_ESCOLAR_ACTUAL, nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiante.id'), nullable=False)


class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    concepto = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), default='Pagado', nullable=False)
    fecha = db.Column(db.String(50), nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiante.id'), nullable=False)


# -----------------------------------------------------------------------------
# COMPATIBILIDAD CON LA BASE DE DATOS ANTERIOR
# create_all() no agrega columnas a tablas existentes. Estas instrucciones
# incorporan las columnas nuevas sin borrar los registros que ya existen.
# -----------------------------------------------------------------------------
def migrar_esquema_existente():
    inspector = inspect(db.engine)
    tablas = inspector.get_table_names()

    if 'estudiante' in tablas:
        columnas = {col['name'] for col in inspector.get_columns('estudiante')}
        if 'estado_academico' not in columnas:
            db.session.execute(text(
                "ALTER TABLE estudiante ADD COLUMN estado_academico VARCHAR(20) NOT NULL DEFAULT 'Activo'"
            ))

    if 'nota' in tablas:
        columnas = {col['name'] for col in inspector.get_columns('nota')}
        if 'anio_escolar' not in columnas:
            db.session.execute(text(
                f'ALTER TABLE nota ADD COLUMN anio_escolar INTEGER NOT NULL DEFAULT {ANIO_ESCOLAR_ACTUAL}'
            ))

    db.session.commit()


with app.app_context():
    db.create_all()
    migrar_esquema_existente()

    # Se crea un administrador inicial solamente si todavía no existe.
    if not Usuario.query.filter_by(username='admin').first():
        db.session.add(Usuario(
            username='admin',
            password=generate_password_hash('1234'),
            rol='admin'
        ))
        db.session.commit()


def asegurar_notas_estudiante(estudiante, anio_escolar=ANIO_ESCOLAR_ACTUAL):
    """Crea las asignaturas que falten sin duplicar las ya registradas."""
    existentes = {
        nota.materia for nota in Nota.query.filter_by(
            estudiante_id=estudiante.id,
            anio_escolar=anio_escolar
        ).all()
    }
    for materia in obtener_materias_por_grado(estudiante.grado):
        if materia not in existentes:
            db.session.add(Nota(
                materia=materia,
                estudiante_id=estudiante.id,
                anio_escolar=anio_escolar
            ))
    db.session.commit()


def usuario_actual_es_admin():
    return session.get('user_id') is not None and session.get('rol') == 'admin'


def maestro_puede_ver(estudiante):
    return (
        session.get('rol') == 'admin'
        or (
            session.get('rol') == 'maestro'
            and estudiante.grado == session.get('grado_asignado')
        )
    )


def validar_nota(valor):
    """Convierte una calificación a float y evita valores inválidos."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError('Todas las calificaciones deben ser números.')
    if not 0 <= numero <= 100:
        raise ValueError('Las calificaciones deben estar entre 0 y 100.')
    return numero


# -----------------------------------------------------------------------------
# AUTENTICACIÓN
# Acepta hashes del primer código y contraseñas antiguas en texto plano del
# segundo código; cuando entra una contraseña antigua, la convierte a hash.
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = Usuario.query.filter_by(username=username).first()

        valido = False
        if user:
            try:
                valido = check_password_hash(user.password, password)
            except (ValueError, TypeError):
                valido = False

            # Compatibilidad temporal con usuarios creados por el código 2.
            if not valido and user.password == password:
                valido = True
                user.password = generate_password_hash(password)
                db.session.commit()

        if valido:
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['rol'] = user.rol
            session['grado_asignado'] = user.grado_asignado
            return redirect(url_for('dashboard'))

        error = 'Usuario o contraseña incorrectos'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# -----------------------------------------------------------------------------
# DASHBOARD Y ESTUDIANTES
# -----------------------------------------------------------------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    rol = session.get('rol')
    grado_asignado = session.get('grado_asignado')
    if rol == 'admin':
        estudiantes = Estudiante.query.order_by(Estudiante.nombre).all()
    else:
        estudiantes = Estudiante.query.filter_by(
            grado=grado_asignado
        ).order_by(Estudiante.nombre).all()

    return render_template(
        'dashboard.html', rol=rol, estudiantes=estudiantes,
        grado_asignado=grado_asignado
    )


@app.route('/agregar', methods=['POST'])
def agregar_estudiante():
    if not usuario_actual_es_admin():
        return redirect(url_for('dashboard'))

    nombre = (request.form.get('nombre') or '').strip()
    grado = (request.form.get('grado') or '').strip()
    if not nombre or not grado:
        flash('Debes indicar el nombre y el grado del estudiante.', 'error')
        return redirect(url_for('dashboard'))

    nuevo = Estudiante(
        nombre=nombre, grado=grado,
        estado_pago='Al día', estado_academico='Activo'
    )
    db.session.add(nuevo)
    db.session.flush()

    for materia in obtener_materias_por_grado(grado):
        db.session.add(Nota(
            materia=materia,
            estudiante_id=nuevo.id,
            anio_escolar=ANIO_ESCOLAR_ACTUAL
        ))

    db.session.commit()
    return redirect(url_for('dashboard'))


# -----------------------------------------------------------------------------
# USUARIOS Y DOCENTES (SOLO ADMINISTRADOR)
# Mantiene /usuarios y /agregar_usuario del primer código y acepta el
# formulario POST directo a /usuarios usado por el segundo código.
# -----------------------------------------------------------------------------
@app.route('/usuarios', methods=['GET', 'POST'])
def gestionar_usuarios():
    if not usuario_actual_es_admin():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        return agregar_usuario()

    usuarios = Usuario.query.order_by(Usuario.username).all()
    docentes = Usuario.query.filter_by(rol='maestro').order_by(Usuario.username).all()
    return render_template('usuarios.html', usuarios=usuarios, docentes=docentes)


@app.route('/agregar_usuario', methods=['POST'])
def agregar_usuario():
    if not usuario_actual_es_admin():
        return redirect(url_for('dashboard'))

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    rol = (request.form.get('rol') or 'maestro').strip()
    grado_asignado = (request.form.get('grado_asignado') or '').strip() if rol == 'maestro' else None

    if not username or not password or rol not in ['admin', 'maestro']:
        flash('Completa los datos del usuario y selecciona un rol válido.', 'error')
        return redirect(url_for('gestionar_usuarios'))
    if rol == 'maestro' and not grado_asignado:
        flash('Debes asignar un grado al maestro.', 'error')
        return redirect(url_for('gestionar_usuarios'))
    if Usuario.query.filter_by(username=username).first():
        flash('Ese nombre de usuario ya existe.', 'error')
        return redirect(url_for('gestionar_usuarios'))

    db.session.add(Usuario(
        username=username,
        password=generate_password_hash(password),
        rol=rol,
        grado_asignado=grado_asignado
    ))
    db.session.commit()
    return redirect(url_for('gestionar_usuarios'))


@app.route('/eliminar_usuario/<int:id>', methods=['POST'])
def eliminar_usuario(id):
    if not usuario_actual_es_admin():
        return redirect(url_for('dashboard'))

    usuario = Usuario.query.get_or_404(id)
    if usuario.id == session.get('user_id'):
        flash('No puedes eliminar el usuario con el que has iniciado sesión.', 'error')
        return redirect(url_for('gestionar_usuarios'))

    db.session.delete(usuario)
    db.session.commit()
    return redirect(url_for('gestionar_usuarios'))


# -----------------------------------------------------------------------------
# CALIFICACIONES POR ASIGNATURA
# Acepta los nombres de campos del segundo código (b1_ID, b2_ID...) y también
# los campos antiguos bimestre_1... del primer código para compatibilidad.
# -----------------------------------------------------------------------------
@app.route('/estudiante/<int:estudiante_id>/notas', methods=['GET', 'POST'])
def gestionar_notas(estudiante_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    estudiante = Estudiante.query.get_or_404(estudiante_id)
    if not maestro_puede_ver(estudiante):
        return redirect(url_for('dashboard'))

    asegurar_notas_estudiante(estudiante)
    notas = Nota.query.filter(
        Nota.estudiante_id == estudiante.id,
        Nota.anio_escolar == ANIO_ESCOLAR_ACTUAL,
        Nota.materia != 'Evaluación General'
    ).order_by(Nota.id).all()

    if request.method == 'POST':
        try:
            for nota in notas:
                # Formato del código 2: b1_<id>, b2_<id>, etc.
                if f'b1_{nota.id}' in request.form:
                    valores = [
                        request.form.get(f'b1_{nota.id}', 0),
                        request.form.get(f'b2_{nota.id}', 0),
                        request.form.get(f'b3_{nota.id}', 0),
                        request.form.get(f'b4_{nota.id}', 0),
                    ]
                # Formato del primer código: un único registro con bimestre_1...
                elif len(notas) == 1 and 'bimestre_1' in request.form:
                    valores = [
                        request.form.get('bimestre_1', 0),
                        request.form.get('bimestre_2', 0),
                        request.form.get('bimestre_3', 0),
                        request.form.get('bimestre_4', 0),
                    ]
                else:
                    # Si el formulario no envió campos para esta materia, no
                    # sobrescribe sus calificaciones existentes.
                    continue

                b1, b2, b3, b4 = [validar_nota(v) for v in valores]
                nota.bimestre_1 = b1
                nota.bimestre_2 = b2
                nota.bimestre_3 = b3
                nota.bimestre_4 = b4
                nota.promedio_final = (b1 + b2 + b3 + b4) / 4.0

            db.session.commit()
            flash('Calificaciones guardadas correctamente.', 'success')
            return redirect(url_for('gestionar_notas', estudiante_id=estudiante.id))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'error')

    # 'nota' conserva compatibilidad con plantillas antiguas de registro único.
    nota = notas[0] if notas else None
    return render_template(
        'notas.html', estudiante=estudiante, notas=notas, nota=nota,
        anio_escolar=ANIO_ESCOLAR_ACTUAL
    )


# -----------------------------------------------------------------------------
# PAGOS (SOLO ADMINISTRADOR)
# -----------------------------------------------------------------------------
@app.route('/estudiante/<int:estudiante_id>/pagos', methods=['GET', 'POST'])
def gestionar_pagos(estudiante_id):
    if not usuario_actual_es_admin():
        return redirect(url_for('dashboard'))

    estudiante = Estudiante.query.get_or_404(estudiante_id)
    pagos = Pago.query.filter_by(estudiante_id=estudiante.id).order_by(Pago.id.desc()).all()

    if request.method == 'POST':
        concepto = (request.form.get('concepto') or '').strip()
        fecha = (request.form.get('fecha') or '').strip()
        estado = request.form.get('estado') or 'Pagado'
        try:
            monto = float(request.form.get('monto', 0))
            if monto < 0:
                raise ValueError
        except ValueError:
            flash('El monto debe ser un número válido mayor o igual a cero.', 'error')
            return redirect(url_for('gestionar_pagos', estudiante_id=estudiante.id))

        if not concepto or not fecha or estado not in ['Pagado', 'Pendiente']:
            flash('Completa los datos del pago correctamente.', 'error')
            return redirect(url_for('gestionar_pagos', estudiante_id=estudiante.id))

        db.session.add(Pago(
            concepto=concepto, monto=monto, estado=estado,
            fecha=fecha, estudiante_id=estudiante.id
        ))
        db.session.flush()
        actualizar_estado_pago(estudiante)
        db.session.commit()
        return redirect(url_for('gestionar_pagos', estudiante_id=estudiante.id))

    return render_template('pagos.html', estudiante=estudiante, pagos=pagos)


def actualizar_estado_pago(estudiante):
    pendientes = Pago.query.filter_by(
        estudiante_id=estudiante.id, estado='Pendiente'
    ).count()
    estudiante.estado_pago = 'Pendiente' if pendientes else 'Al día'


@app.route('/pago/<int:pago_id>/eliminar/<int:estudiante_id>', methods=['POST'])
def eliminar_pago(pago_id, estudiante_id):
    if not usuario_actual_es_admin():
        return redirect(url_for('dashboard'))

    estudiante = Estudiante.query.get_or_404(estudiante_id)
    pago = Pago.query.get_or_404(pago_id)
    if pago.estudiante_id != estudiante.id:
        return redirect(url_for('gestionar_pagos', estudiante_id=estudiante.id))

    db.session.delete(pago)
    db.session.flush()
    actualizar_estado_pago(estudiante)
    db.session.commit()
    return redirect(url_for('gestionar_pagos', estudiante_id=estudiante.id))

# --- VISTA DE ALUMNOS Y FICHAS CON FILTRO POR GRADO ---
@app.route('/alumnos')
def listar_alumnos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('rol') != 'admin':
        return redirect(url_for('dashboard'))
        
    grado_filtro = request.args.get('grado', 'todos')
    rol = session.get('rol')
    grado_asignado = session.get('grado_asignado')
    
    # Si es maestro, solo ve su grado asignado
    if rol == 'maestro':
        estudiantes = Estudiante.query.filter_by(grado=grado_asignado).all()
    else:
        if grado_filtro and grado_filtro != 'todos':
            estudiantes = Estudiante.query.filter_by(grado=grado_filtro).all()
        else:
            estudiantes = Estudiante.query.all()
            
    grados_disponibles = ['Pre-kinder', 'Kínder', 'Preparatoria', '1ro Primaria', '2do Primaria', '3ro Primaria', '4to Primaria', '5to Primaria', '6to Primaria']
    return render_template('alumnos.html', estudiantes=estudiantes, grados=grados_disponibles, grado_seleccionado=grado_filtro, rol=rol)


# --- VISTA DE CALIFICACIONES / PLANILLAS POR GRADO ---
@app.route('/calificaciones')
def gestionar_calificaciones():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    rol = session.get('rol')
    grado_asignado = session.get('grado_asignado')
    
    if rol == 'maestro':
        grado_filtro = grado_asignado
    else:
        grado_filtro = request.args.get('grado', 'Pre-kinder')
        
    estudiantes = Estudiante.query.filter_by(grado=grado_filtro).all() if grado_filtro else []
    grados_disponibles = ['Pre-kinder', 'Kínder', 'Preparatoria', '1ro Primaria', '2do Primaria', '3ro Primaria', '4to Primaria', '5to Primaria', '6to Primaria']
    
    return render_template('calificaciones.html', estudiantes=estudiantes, grados=grados_disponibles, grado_seleccionado=grado_filtro, rol=rol)
# -----------------------------------------------------------------------------
# PDF: BOLETA INDIVIDUAL
# -----------------------------------------------------------------------------
def estilos_pdf():
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle(
        'TituloColegio', parent=styles['Heading1'], fontSize=15,
        textColor=colors.HexColor('#065F46'), alignment=1, spaceAfter=4
    )
    subtitulo = ParagraphStyle(
        'SubtituloColegio', parent=styles['Normal'], fontSize=9,
        textColor=colors.HexColor('#4B5563'), alignment=1, spaceAfter=12
    )
    cuerpo = ParagraphStyle(
        'CuerpoColegio', parent=styles['Normal'], fontSize=9,
        textColor=colors.HexColor('#1F2937'), spaceAfter=4
    )
    return titulo, subtitulo, cuerpo


def agregar_encabezado_pdf(elements, subtitulo_texto, logo_size=50):
    titulo, subtitulo, _ = estilos_pdf()
    try:
        logo = Image('static/logo.png', width=logo_size, height=logo_size)
        logo.hAlign = 'CENTER'
        elements.extend([logo, Spacer(1, 4)])
    except Exception:
        pass
    elements.append(Paragraph('CENTRO EDUCATIVO ESPERANZA PARA GUATEMALA', titulo))
    elements.append(Paragraph(subtitulo_texto, subtitulo))


@app.route('/estudiante/<int:estudiante_id>/boleta-pdf')
def descargar_boleta_pdf(estudiante_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    estudiante = Estudiante.query.get_or_404(estudiante_id)
    if not maestro_puede_ver(estudiante):
        return redirect(url_for('dashboard'))

    asegurar_notas_estudiante(estudiante)
    notas = Nota.query.filter(
        Nota.estudiante_id == estudiante.id,
        Nota.anio_escolar == ANIO_ESCOLAR_ACTUAL,
        Nota.materia != 'Evaluación General'
    ).order_by(Nota.materia).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=35, leftMargin=35,
        topMargin=30, bottomMargin=35
    )
    elements = []
    agregar_encabezado_pdf(
        elements, f'Boleta de Calificaciones - Ciclo Escolar {ANIO_ESCOLAR_ACTUAL}', 55
    )
    _, _, cuerpo = estilos_pdf()
    elements.extend([
        Paragraph(f'<b>Nombre del Alumno(a):</b> {estudiante.nombre}', cuerpo),
        Paragraph(f'<b>Nivel / Grado:</b> {estudiante.grado}', cuerpo),
        Paragraph(f'<b>Estado Académico:</b> {estudiante.estado_academico}', cuerpo),
        Paragraph(f'<b>Estado Financiero:</b> {estudiante.estado_pago}', cuerpo),
        Spacer(1, 8),
    ])

    data = [['Asignatura', 'B1', 'B2', 'B3', 'B4', 'Promedio', 'Estado']]
    for nota in notas:
        estado = 'Aprobado' if nota.promedio_final >= 60 else 'Reprobado'
        data.append([
            Paragraph(nota.materia, cuerpo),
            f'{nota.bimestre_1:.1f}', f'{nota.bimestre_2:.1f}',
            f'{nota.bimestre_3:.1f}', f'{nota.bimestre_4:.1f}',
            f'{nota.promedio_final:.1f}', estado
        ])

    tabla = Table(data, colWidths=[220, 42, 42, 42, 42, 60, 65], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#065F46')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.extend([tabla, Spacer(1, 28)])

    firmas = Table([
        ['___________________________________', '___________________________________'],
        ['Firma del Docente de Grado', 'Firma y Sello de Dirección']
    ], colWidths=[250, 250])
    firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#4B5563')),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(firmas)

    doc.build(elements)
    buffer.seek(0)
    filename = f"Boleta_{estudiante.nombre.replace(' ', '_')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


# -----------------------------------------------------------------------------
# PDF: PLANILLA CONSOLIDADA POR GRADO
# -----------------------------------------------------------------------------
@app.route('/grado/<string:grado_nombre>/planilla-pdf')
def descargar_planilla_grado_pdf(grado_nombre):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    estudiantes = Estudiante.query.filter_by(grado=grado_nombre).all()
    if not estudiantes:
        return redirect(url_for('dashboard'))
        
    buffer = io.BytesIO()
    # Cambiamos a LANDSCAPE (Horizontal) para aprovechar todo el ancho de la hoja
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#065F46'), alignment=1, spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#4B5563'), alignment=1, spaceAfter=15)
    
    # Estilo especial para los encabezados de las materias (permite que el texto baje de línea)
    header_cell_style = ParagraphStyle(
        'HeaderCellStyle',
        parent=styles['Normal'],
        fontSize=7.5,
        leading=9,
        textColor=colors.whitesmoke,
        alignment=1, # Centrado
        fontName='Helvetica-Bold'
    )
    
    row_cell_style = ParagraphStyle(
        'RowCellStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#1F2937'),
        alignment=1,
        fontName='Helvetica'
    )

    name_cell_style = ParagraphStyle(
        'NameCellStyle',
        parent=styles['Normal'],
        fontSize=8.5,
        textColor=colors.HexColor('#1F2937'),
        alignment=0, # Izquierda para nombres
        fontName='Helvetica-Bold'
    )

    try:
        logo = Image('static/logo.png', width=45, height=45)
        logo.hAlign = 'CENTER'
        elements.append(logo)
        elements.append(Spacer(1, 4))
    except:
        pass

    elements.append(Paragraph("CENTRO EDUCATIVO ESPERANZA PARA GUATEMALA", title_style))
    elements.append(Paragraph(f"Consolidado Oficial de Promedios - Grado: {grado_nombre} - Ciclo Escolar 2026", subtitle_style))
    
    materias_grado = obtener_materias_por_grado(grado_nombre)
    
    # Envolver los títulos largos en Paragraphs para que el texto baje ordenadamente
    encabezados = [Paragraph("Estudiante", header_cell_style)]
    for m in materias_grado:
        # Abreviamos nombres muy largos o dejamos que el Paragraph los ajuste
        encabezados.append(Paragraph(m, header_cell_style))
    encabezados.append(Paragraph("Prom. Gral.", header_cell_style))
    
    data_tabla = [encabezados]
    
    for e in estudiantes:
        fila = [Paragraph(e.nombre, name_cell_style)]
        suma = 0
        conteo = 0
        for mat in materias_grado:
            nota = Nota.query.filter_by(estudiante_id=e.id, materia=mat).first()
            prom = nota.promedio_final if nota else 0.0
            texto_nota = f"{prom:.1f}" if prom > 0 else "-"
            fila.append(Paragraph(texto_nota, row_cell_style))
            if prom > 0:
                suma += prom
                conteo += 1
        prom_general = (suma / conteo) if conteo > 0 else 0.0
        
        prom_cell_style = ParagraphStyle('PromStyle', parent=row_cell_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#065F46'))
        fila.append(Paragraph(f"{prom_general:.1f}", prom_cell_style))
        data_tabla.append(fila)
        
    # Anchos calculados de forma óptima para hoja horizontal (Total ancho aprox ~730 puntos)
    num_materias = len(materias_grado)
    ancho_materia = 520 / num_materias # Distribuye el espacio sobrante equitativamente entre las materias
    col_widths = [140] + [ancho_materia] * num_materias + [60]
    
    t = Table(data_tabla, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#065F46')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (-1, 1), (-1, -1), colors.HexColor('#E6FFFA')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 30))
    
    firma_data = [
        ['___________________________________', '___________________________________'],
        ['Firma del Docente de Grado', 'Firma y Sello de Dirección']
    ]
    t_firmas = Table(firma_data, colWidths=[250, 250])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#4B5563')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(t_firmas)
    
    doc.build(elements)
    buffer.seek(0)
    filename = f"Consolidado_{grado_nombre.replace(' ', '_')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


if __name__ == '__main__':
    app.run(debug=True)

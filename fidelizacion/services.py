"""Reusable business logic for the loyalty / fidelizacion system."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, Optional

from django.db import transaction
from django.utils import timezone

from clientes.models import Cliente
from fidelizacion.models import ConfigPuntos, HistorialPuntos


class LoyaltyError(Exception):
    """Raised when a loyalty operation cannot be completed."""


@dataclass(frozen=True)
class LoyaltyComputation:
    puntos: int
    subtotal_cop: Decimal
    descripcion: str = ""
    puntos_base: int = 0
    bono_nivel: int = 0
    bono_extra: int = 0
    metadata: Optional[Dict[str, Any]] = None


def get_config() -> ConfigPuntos:
    """Convenience wrapper."""
    return ConfigPuntos.load()


def servicio_permite_puntos(servicio, config: Optional[ConfigPuntos] = None) -> bool:
    """Return True when the given service/category is allowed to earn points."""
    if servicio is None:
        return True
    config = config or get_config()
    try:
        if config.exclusiones_servicios.filter(pk=servicio.pk).exists():
            return False
    except Exception:
        pass
    lista_exclu = config.exclusiones_categorias or []
    categoria = getattr(servicio, "categoria", None)
    if categoria and categoria in lista_exclu:
        return False
    return True


def _parse_niveles(config: ConfigPuntos) -> list[Dict[str, Any]]:
    """Return normalized level configuration with thresholds and benefits."""
    raw = config.niveles_config or {}
    if not isinstance(raw, dict):
        return []
    niveles: list[Dict[str, Any]] = []
    for nombre, valor in raw.items():
        if isinstance(valor, dict):
            raw_umbral = valor.get("umbral", valor.get("threshold", valor.get("minimo")))
            raw_multiplicador = valor.get("multiplicador", valor.get("factor", 1))
            raw_bono = valor.get("bono_fijo", valor.get("bono", 0))
        else:
            raw_umbral = valor
            raw_multiplicador = 1
            raw_bono = 0
        try:
            umbral = max(int(raw_umbral or 0), 0)
        except (TypeError, ValueError):
            continue
        try:
            multiplicador = float(raw_multiplicador or 1)
        except (TypeError, ValueError):
            multiplicador = 1.0
        try:
            bono_fijo = int(raw_bono or 0)
        except (TypeError, ValueError):
            bono_fijo = 0
        niveles.append(
            {
                "nombre": str(nombre),
                "umbral": umbral,
                "multiplicador": round(max(multiplicador, 0.0), 4),
                "bono_fijo": max(bono_fijo, 0),
            }
        )
    niveles.sort(key=lambda item: (item["umbral"], item["nombre"]))
    return niveles


def _nivel_para_saldo(niveles: Iterable[Dict[str, Any]], saldo: int) -> Optional[Dict[str, Any]]:
    """Pick the highest level allowed for the current balance."""
    elegido: Optional[Dict[str, Any]] = None
    max_umbral = -1
    for nivel in niveles:
        try:
            umbral = int(nivel.get("umbral", 0))
        except (TypeError, ValueError):
            continue
        if saldo >= umbral and umbral >= max_umbral:
            elegido = nivel
            max_umbral = umbral
    return elegido


def _format_decimal(value: Decimal) -> str:
    """Render Decimal values without trailing zeros."""
    value_str = f"{value:.4f}"
    value_str = value_str.rstrip("0").rstrip(".")
    return value_str or "0"


def calcular_puntos_detallado(
    subtotal_cop: Decimal,
    config: Optional[ConfigPuntos] = None,
    cliente: Optional[Cliente] = None,
    niveles: Optional[Iterable[Dict[str, Any]]] = None,
) -> LoyaltyComputation:
    """Calcula los puntos con un detalle completo del calculo."""
    config = config or get_config()
    niveles_list = list(niveles) if niveles is not None else _parse_niveles(config)

    if subtotal_cop is None:
        return LoyaltyComputation(0, Decimal("0"), "Subtotal no valido.", metadata={"motivo": "subtotal_nulo"})

    try:
        subtotal = Decimal(subtotal_cop)
    except (InvalidOperation, TypeError, ValueError):
        return LoyaltyComputation(0, Decimal("0"), "Subtotal no valido.", metadata={"motivo": "subtotal_invalido"})

    metadata: Dict[str, Any] = {
        "subtotal_cop": str(subtotal.quantize(Decimal("1.00")) if subtotal.as_tuple().exponent < -2 else subtotal),
        "puntos_por_monto": int(getattr(config, "puntos_por_monto", 0) or 0),
        "monto_base_cop": int(getattr(config, "monto_base_cop", 0) or 0),
    }

    if subtotal <= 0:
        return LoyaltyComputation(0, subtotal, "Subtotal insuficiente para generar puntos.", metadata=metadata)
    if config.monto_base_cop <= 0 or config.puntos_por_monto <= 0:
        metadata["motivo"] = "config_incompleta"
        return LoyaltyComputation(0, subtotal, "Configuracion de puntos incompleta.", metadata=metadata)

    puntos_unitarios = Decimal(config.puntos_por_monto)
    monto_base = Decimal(config.monto_base_cop)
    puntos_base_decimal = (subtotal * puntos_unitarios) / monto_base
    puntos_base = max(int(puntos_base_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP)), 0)

    descripcion_partes: list[str] = []
    if puntos_base > 0:
        descripcion_partes.append(
            f"{puntos_base} pts base ({config.puntos_por_monto} por cada {config.monto_base_cop} COP)"
        )
    else:
        descripcion_partes.append(
            f"Compra inferior a la unidad base de {config.monto_base_cop} COP"
        )

    bonus_nivel = 0
    bonus_extra = 0
    nivel_origen = None

    if cliente is not None:
        saldo = int(getattr(cliente, "puntos_saldo", 0) or 0)
        nivel_origen = _nivel_para_saldo(niveles_list, saldo)
        if not nivel_origen and getattr(cliente, "nivel", ""):
            nivel_origen = next((n for n in niveles_list if n["nombre"] == cliente.nivel), None)

        if nivel_origen:
            multiplicador = Decimal(str(nivel_origen.get("multiplicador", 1) or 1))
            multiplicador = multiplicador if multiplicador >= 0 else Decimal("0")
            puntos_con_multiplicador = int(
                (Decimal(puntos_base) * multiplicador).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
            bonus_nivel = puntos_con_multiplicador - puntos_base
            metadata["multiplicador"] = float(multiplicador)
            metadata["nivel_origen"] = nivel_origen["nombre"]
            if bonus_nivel != 0:
                signo = "+" if bonus_nivel > 0 else ""
                descripcion_partes.append(
                    f"{signo}{bonus_nivel} pts por nivel {nivel_origen['nombre']} x{_format_decimal(multiplicador)}"
                )
            bonus_extra = max(int(nivel_origen.get("bono_fijo", 0) or 0), 0)
            if bonus_extra:
                descripcion_partes.append(
                    f"+{bonus_extra} pts bono fijo nivel {nivel_origen['nombre']}"
                )
        else:
            metadata["nivel_origen"] = ""
            metadata["multiplicador"] = 1.0
    else:
        metadata["nivel_origen"] = ""
        metadata["multiplicador"] = 1.0

    total_puntos = puntos_base + bonus_nivel + bonus_extra
    if total_puntos < 0:
        total_puntos = 0

    metadata["puntos_base"] = puntos_base
    metadata["ajuste_nivel"] = bonus_nivel
    metadata["bono_extra"] = bonus_extra

    tope = int(getattr(config, "puntos_max_por_factura", 0) or 0)
    if tope and total_puntos > tope:
        descripcion_partes.append(f"Tope maximo {tope} pts aplicado")
        metadata["tope_aplicado"] = tope
        total_puntos = tope

    if cliente is not None and niveles_list:
        saldo_final = int(getattr(cliente, "puntos_saldo", 0) or 0) + total_puntos
        siguiente = next((n for n in niveles_list if int(n.get("umbral", 0)) > saldo_final), None)
        if siguiente:
            faltantes = max(int(siguiente.get("umbral", 0)) - saldo_final, 0)
            metadata["proximo_nivel"] = {
                "nombre": siguiente.get("nombre", ""),
                "umbral": int(siguiente.get("umbral", 0)),
                "faltantes": faltantes,
            }

    descripcion = "; ".join(descripcion_partes)
    metadata["puntos_total"] = total_puntos

    return LoyaltyComputation(
        puntos=total_puntos,
        subtotal_cop=subtotal,
        descripcion=descripcion,
        puntos_base=puntos_base,
        bono_nivel=bonus_nivel,
        bono_extra=bonus_extra,
        metadata=metadata,
    )


def calcular_puntos(
    subtotal_cop: Decimal,
    config: Optional[ConfigPuntos] = None,
    cliente: Optional[Cliente] = None,
) -> int:
    """Compat wrapper que entrega solo el total de puntos."""
    return calcular_puntos_detallado(subtotal_cop, config=config, cliente=cliente).puntos


def calcular_redencion_cop(puntos: int, config: Optional[ConfigPuntos] = None) -> Decimal:
    """Convierte puntos a valor en COP segun la configuracion vigente."""
    config = config or get_config()
    if puntos <= 0 or config.puntos_equivalencia <= 0:
        return Decimal("0.00")
    factor = Decimal(config.valor_redencion_cop) / Decimal(config.puntos_equivalencia)
    return (Decimal(puntos) * factor).quantize(Decimal("1.00"))


def _actualizar_nivel(
    cliente: Cliente,
    config: ConfigPuntos,
    niveles: Optional[Iterable[Dict[str, Any]]] = None,
) -> None:
    niveles_list = list(niveles) if niveles is not None else _parse_niveles(config)
    if not niveles_list:
        if cliente.nivel:
            cliente.nivel = ""
        return
    nivel_obj = _nivel_para_saldo(niveles_list, cliente.puntos_saldo)
    nuevo_nivel = nivel_obj["nombre"] if nivel_obj else ""
    if nuevo_nivel != (cliente.nivel or ""):
        cliente.nivel = nuevo_nivel


@transaction.atomic
def otorgar_puntos(
    cliente: Cliente,
    subtotal_cop: Decimal,
    referencia: str,
    usuario_admin=None,
    motivo: str = "",
    servicio=None,
) -> int:
    '''Acredita puntos al cliente segun el subtotal y registra el movimiento.'''
    config = get_config()
    if not servicio_permite_puntos(servicio, config=config):
        return 0

    cliente_locked = Cliente.objects.select_for_update().get(pk=cliente.pk)
    niveles = _parse_niveles(config)
    calculo = calcular_puntos_detallado(
        subtotal_cop,
        config=config,
        cliente=cliente_locked,
        niveles=niveles,
    )
    puntos = calculo.puntos
    if puntos <= 0:
        return 0

    cliente_locked.puntos_saldo += puntos
    _actualizar_nivel(cliente_locked, config, niveles=niveles)
    cliente_locked.save(update_fields=["puntos_saldo", "nivel", "actualizado"])

    subtotal_decimal = calculo.subtotal_cop.quantize(Decimal("1.00"))
    metadata_historial = dict(calculo.metadata or {})
    metadata_historial.setdefault("detalle", calculo.descripcion)
    metadata_historial["puntos_ganados"] = puntos
    metadata_historial["servicio_id"] = getattr(servicio, "pk", None)
    if servicio is not None:
        metadata_historial["servicio"] = getattr(servicio, "nombre", str(servicio))

    HistorialPuntos.objects.create(
        cliente=cliente_locked,
        tipo=HistorialPuntos.Tipo.GANA,
        fecha=timezone.now(),
        monto_pesos=subtotal_decimal,
        puntos_ganados=puntos,
        saldo_resultante=cliente_locked.puntos_saldo,
        referencia=referencia,
        usuario_admin=usuario_admin,
        motivo=motivo or calculo.descripcion or "Otorgamiento automatico",
        metadata=metadata_historial,
    )
    return puntos

@transaction.atomic
def canjear_puntos(cliente: Cliente, puntos: int, referencia: str, usuario_admin=None, motivo="") -> Decimal:
    """Debita puntos del cliente, valida saldo y registra el descuento."""
    if puntos <= 0:
        raise LoyaltyError("La cantidad de puntos a redimir debe ser positiva.")

    config = get_config()
    valor_cop = calcular_redencion_cop(puntos, config=config)
    if valor_cop <= 0:
        raise LoyaltyError("La configuracion de conversion de puntos no produce descuento valido.")

    cliente_locked = Cliente.objects.select_for_update().get(pk=cliente.pk)
    if cliente_locked.puntos_saldo < puntos:
        raise LoyaltyError("El cliente no tiene puntos suficientes.")

    cliente_locked.puntos_saldo -= puntos
    _actualizar_nivel(cliente_locked, config)
    cliente_locked.save(update_fields=["puntos_saldo", "nivel", "actualizado"])

    HistorialPuntos.objects.create(
        cliente=cliente_locked,
        tipo=HistorialPuntos.Tipo.USA,
        fecha=timezone.now(),
        monto_pesos=valor_cop * Decimal("-1"),
        puntos_usados=puntos,
        saldo_resultante=cliente_locked.puntos_saldo,
        referencia=referencia,
        usuario_admin=usuario_admin,
        motivo=motivo or "Canje aplicado",
    )
    return valor_cop


@transaction.atomic
def bonificar_puntos(cliente: Cliente, puntos: int, referencia: str, usuario_admin=None, motivo="Bonificacion manual") -> None:
    if puntos == 0:
        raise LoyaltyError("Debe especificar puntos diferentes de cero para el ajuste.")

    cliente_locked = Cliente.objects.select_for_update().get(pk=cliente.pk)
    config = get_config()

    nuevo_saldo = cliente_locked.puntos_saldo + puntos
    if nuevo_saldo < 0:
        raise LoyaltyError("El ajuste dejaria el saldo del cliente en negativo.")

    cliente_locked.puntos_saldo = nuevo_saldo
    _actualizar_nivel(cliente_locked, config)
    cliente_locked.save(update_fields=["puntos_saldo", "nivel", "actualizado"])

    tipo = HistorialPuntos.Tipo.BONO if puntos > 0 else HistorialPuntos.Tipo.AJUSTE

    HistorialPuntos.objects.create(
        cliente=cliente_locked,
        tipo=tipo,
        fecha=timezone.now(),
        monto_pesos=Decimal("0.00"),
        puntos_ganados=max(puntos, 0),
        puntos_usados=abs(puntos) if puntos < 0 else 0,
        saldo_resultante=cliente_locked.puntos_saldo,
        referencia=referencia,
        usuario_admin=usuario_admin,
        motivo=motivo,
    )


@transaction.atomic
def revertir_puntos(cliente: Cliente, referencia: str, usuario_admin=None, motivo="Reversion automatica") -> int:
    movimientos = HistorialPuntos.objects.select_for_update().filter(cliente=cliente, referencia=referencia)
    if not movimientos.exists():
        raise LoyaltyError("No se encontraron movimientos asociados a la referencia indicada.")

    delta = sum(m.puntos_ganados - m.puntos_usados for m in movimientos)
    if delta == 0:
        return 0

    cliente_locked = Cliente.objects.select_for_update().get(pk=cliente.pk)
    nuevo_saldo = cliente_locked.puntos_saldo - delta
    if nuevo_saldo < 0:
        nuevo_saldo = 0

    cliente_locked.puntos_saldo = nuevo_saldo
    config = get_config()
    _actualizar_nivel(cliente_locked, config)
    cliente_locked.save(update_fields=["puntos_saldo", "nivel", "actualizado"])

    HistorialPuntos.objects.create(
        cliente=cliente_locked,
        tipo=HistorialPuntos.Tipo.REVERSA,
        fecha=timezone.now(),
        monto_pesos=Decimal("0.00"),
        puntos_usados=max(delta, 0),
        puntos_ganados=abs(delta) if delta < 0 else 0,
        saldo_resultante=cliente_locked.puntos_saldo,
        referencia=referencia,
        usuario_admin=usuario_admin,
        motivo=motivo,
    )
    return delta


def obtener_saldo(cliente: Cliente) -> int:
    cliente.refresh_from_db(fields=["puntos_saldo"])
    return cliente.puntos_saldo


def obtener_historial(cliente: Cliente, limit: Optional[int] = None) -> Iterable[HistorialPuntos]:
    qs = cliente.movimientos_puntos.select_related("usuario_admin").order_by("-fecha")
    if limit:
        qs = qs[:limit]
    return qs

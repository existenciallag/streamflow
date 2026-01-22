# models.py
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, ForeignKey, Table
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# --- Tables (mapped to your Supabase schema, simplified for SQLite) ---

class Brand(Base):
    __tablename__ = "brands"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=False)
    team_id = Column(String, nullable=True)

class CytometerOpticalChannel(Base):
    __tablename__ = "cytometer_optical_channels"
    id = Column(String, primary_key=True)
    cytometer_id = Column(String, ForeignKey("cytometers.id"), nullable=True)
    optical_channel_id = Column(String, ForeignKey("optical_channels.id"), nullable=True)
    team_id = Column(String, nullable=True)
    associated_fluorochromes = Column(Text, nullable=True)  # JSON text

class Cytometer(Base):
    __tablename__ = "cytometers"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=False)
    manufacturer = Column(Text, nullable=True)
    model = Column(Text, nullable=True)
    serial_number = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    team_id = Column(String, nullable=True)

class GeneralReagentUnit(Base):
    __tablename__ = "general_reagent_units"
    id = Column(String, primary_key=True)
    general_reagent_id = Column(String, ForeignKey("general_reagents.id"), nullable=False)
    lot_number = Column(Text, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    location = Column(Text, nullable=True)
    status = Column(Text, nullable=True)
    volume = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    team_id = Column(String, nullable=True)

class GeneralReagent(Base):
    __tablename__ = "general_reagents"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=False)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=True)
    type = Column(Text, nullable=True)
    concentration = Column(Text, nullable=True)
    preparation_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    arrival_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    price = Column(Float, nullable=True)
    team_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)

class OpticalChannel(Base):
    __tablename__ = "optical_channels"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=False)
    min_range = Column(Integer, nullable=True)
    max_range = Column(Integer, nullable=True)
    team_id = Column(String, nullable=True)

class PanelCategory(Base):
    __tablename__ = "panel_categories"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=False)
    team_id = Column(String, nullable=True)

class PanelGeneralReagent(Base):
    __tablename__ = "panel_general_reagents"
    id = Column(String, primary_key=True)
    panel_id = Column(String, ForeignKey("panels.id"), nullable=False)
    general_reagent_id = Column(String, ForeignKey("general_reagents.id"), nullable=False)
    volume_used = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    added_at = Column(DateTime, nullable=True)
    team_id = Column(String, nullable=True)

class PanelReagent(Base):
    __tablename__ = "panel_reagents"
    id = Column(String, primary_key=True)
    panel_id = Column(String, ForeignKey("panels.id"), nullable=False)
    reagent_id = Column(String, ForeignKey("reagents.id"), nullable=False)
    optical_channel_id = Column(String, ForeignKey("optical_channels.id"), nullable=True)
    volume_used = Column(Float, nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    is_intracellular = Column(Boolean, nullable=True)
    display_name = Column(Text, nullable=True)
    team_id = Column(String, nullable=True)

class Panel(Base):
    __tablename__ = "panels"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=False)
    category_id = Column(String, ForeignKey("panel_categories.id"), nullable=True)
    description = Column(Text, nullable=True)
    sample_volume = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=True)
    status = Column(Text, nullable=True)
    cytometer_id = Column(String, ForeignKey("cytometers.id"), nullable=True)
    washed_sample = Column(Boolean, nullable=True)
    team_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    acquisition_protocol_status = Column(Text, nullable=True)
    acquisition_protocol_name = Column(Text, nullable=True)
    acquisition_protocol_code = Column(Text, nullable=True)
    compensation_status = Column(Text, nullable=True)
    compensation_name = Column(Text, nullable=True)
    compensation_code = Column(Text, nullable=True)
    analysis_protocol_status = Column(Text, nullable=True)
    analysis_protocol_name = Column(Text, nullable=True)
    analysis_protocol_code = Column(Text, nullable=True)

class PurchaseOrderHistory(Base):
    __tablename__ = "purchase_order_history"
    id = Column(String, primary_key=True)
    purchase_order_id = Column(String, ForeignKey("purchase_orders.id"), nullable=True)
    status = Column(Text, nullable=True)
    changed_at = Column(DateTime, nullable=True)
    team_id = Column(String, nullable=True)

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id = Column(String, primary_key=True)
    purchase_order_id = Column(String, ForeignKey("purchase_orders.id"), nullable=True)
    reagent_id = Column(String, ForeignKey("reagents.id"), nullable=True)
    quantity = Column(Integer, nullable=True)
    unit_price = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    status = Column(Text, nullable=True)
    received_quantity = Column(Integer, nullable=True)
    team_id = Column(String, nullable=True)

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(String, primary_key=True)
    supplier = Column(Text, nullable=True)
    total_price = Column(Float, nullable=True)
    status = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    team_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)

class ReagentHistory(Base):
    __tablename__ = "reagent_history"
    id = Column(String, primary_key=True)
    reagent_id = Column(String, ForeignKey("reagents.id"), nullable=True)
    action = Column(Text, nullable=True)
    changed_by = Column(Text, nullable=True)
    modified_at = Column(DateTime, nullable=True)
    team_id = Column(String, nullable=True)

class ReagentUnit(Base):
    __tablename__ = "reagent_units"
    id = Column(String, primary_key=True)
    reagent_id = Column(String, ForeignKey("reagents.id"), nullable=False)
    initial_volume = Column(Float, nullable=True)
    arrival_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    status = Column(Text, nullable=True)
    lot = Column(Text, nullable=True)
    team_id = Column(String, nullable=True)

class Reagent(Base):
    __tablename__ = "reagents"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=False)
    fluorochrome = Column(Text, nullable=True)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=True)
    catalog_number = Column(Text, nullable=True)
    clone = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    team_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)

class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    team_id = Column(String, nullable=True)

class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    id = Column(String, primary_key=True)
    name = Column(Text, nullable=True)
    fluorochrome = Column(Text, nullable=True)
    suggested_supplier = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    priority = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON text
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    team_id = Column(String, nullable=True)
    reagent_id = Column(String, ForeignKey("reagents.id"), nullable=True)

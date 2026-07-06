# src/schemas.py
"""
Pydantic models for the product enrichment pipeline output.

Updated to support the three-array image structure:
  - scraped_images:   original product photos from the source page (max 7)
  - lifestyle_images: AI-generated lifestyle shots (3x, different angles)
  - feature_images:   AI-generated feature highlight shots (1 per key_feature)
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class StockStatus(str, Enum):
    in_stock      = "in_stock"
    out_of_stock  = "out_of_stock"
    limited_stock = "limited_stock"
    preorder      = "preorder"

class EnrichmentStatus(str, Enum):
    full          = "full"
    partial       = "partial"
    original_only = "original_only"

class ImageGenerationStatus(str, Enum):
    success  = "success"
    partial  = "partial"
    failed   = "failed"
    skipped  = "skipped"

class ImageType(str, Enum):
    product   = "product"
    lifestyle = "lifestyle"
    feature   = "feature"

class ProductCategory(str, Enum):
    pickleball_paddle       = "Pickleball Paddle"
    tennis_racket           = "Tennis / Badminton / Squash Racket"
    treadmill               = "Treadmill"
    exercise_bike           = "Exercise Bike / Cycle"
    dumbbells               = "Dumbbells / Kettlebells / Free Weights"
    yoga_mat                = "Yoga / Pilates Mat"
    resistance_bands        = "Resistance Bands / Tubes"
    general_fitness         = "General Fitness Equipment"


# ── Image models ─────────────────────────────────────────────────────────────

class ScrapedImageItem(BaseModel):
    """Original product image scraped from the source page."""
    url:  str
    alt:  str
    type: ImageType = ImageType.product


class LifestyleImageItem(BaseModel):
    """AI-generated lifestyle image showing a person using the product."""
    url:       str
    alt:       str
    type:      ImageType = ImageType.lifestyle
    drive_url: Optional[str] = None  # Google Drive sharing URL


class FeatureImageItem(BaseModel):
    """AI-generated image highlighting a specific product feature."""
    url:                 str
    alt:                 str
    type:                ImageType = ImageType.feature
    drive_url:           Optional[str] = None
    feature_title:       Optional[str] = None  # e.g. "Carbon Abrasion Surface"
    feature_description: Optional[str] = None  # the feature description used as input


class ImagesOutput(BaseModel):
    """
    Three-array image structure.

    scraped_images   — original product photos from the source (max 7)
    lifestyle_images — AI lifestyle shots (3x, person using the product)
    feature_images   — AI feature shots (1 per key_feature)
    """
    scraped_images:   list[ScrapedImageItem]   = Field(default_factory=list, max_length=7)
    lifestyle_images: list[LifestyleImageItem]  = Field(default_factory=list)
    feature_images:   list[FeatureImageItem]    = Field(default_factory=list)


# ── Shared sub-models ────────────────────────────────────────────────────────

class Pricing(BaseModel):
    price:            str
    compare_at_price: Optional[str] = None
    currency:         str

class KeyFeature(BaseModel):
    title:       str        # 2-4 word feature name
    description: str        # 1-2 sentence benefit explanation

class FeatureTableEntry(BaseModel):
    label: str
    value: str

class FAQ(BaseModel):
    question: str
    answer:   str

class ProductIdentity(BaseModel):
    brand:            Optional[str] = None
    product_name:     Optional[str] = None
    model:            Optional[str] = None
    series:           Optional[str] = None
    sku:              Optional[str] = None
    upc:              Optional[str] = None
    product_category: Optional[str] = None
    product_type:     Optional[str] = None

class EnrichmentMetadata(BaseModel):
    original_source_url:        str
    amazon_source_url:          Optional[str]              = None
    enrichment_status:          EnrichmentStatus
    image_generation_status:    ImageGenerationStatus
    lifestyle_images_generated: int                        = 0
    feature_images_generated:   int                        = 0
    lifestyle_images_failed:    int                        = 0
    feature_images_failed:      int                        = 0
    scraped_images_kept:        int                        = 0
    fields_not_found:           list[str]                  = []


# ── Category-specific specification models ───────────────────────────────────

class PickleballPaddleSpecs(BaseModel):
    surface_material:       Optional[str] = None
    core_material:          Optional[str] = None
    core_type:              Optional[str] = None
    core_thickness:         Optional[str] = None
    finish_surface_texture: Optional[str] = None
    edge_guard:             Optional[str] = None
    handle_grip:            Optional[str] = None
    grip_length:            Optional[str] = None
    grip_circumference:     Optional[str] = None
    paddle_length:          Optional[str] = None
    paddle_width:           Optional[str] = None
    paddle_shape:           Optional[str] = None
    total_weight:           Optional[str] = None
    swing_weight:           Optional[str] = None
    sweet_spot_size:        Optional[str] = None
    spin_rating:            Optional[str] = None
    power_rating:           Optional[str] = None
    control_rating:         Optional[str] = None
    noise_level:            Optional[str] = None
    usapa_approved:         Optional[str] = None
    skill_level:            Optional[str] = None
    playing_style:          Optional[str] = None
    usage:                  Optional[str] = None
    warranty:               Optional[str] = None
    country_of_origin:      Optional[str] = None

class TennisRacketSpecs(BaseModel):
    head_size:                  Optional[str] = None
    head_shape:                 Optional[str] = None
    frame_material:             Optional[str] = None
    string_pattern:             Optional[str] = None
    string_material:            Optional[str] = None
    string_tension_range:       Optional[str] = None
    beam_width:                 Optional[str] = None
    balance_point:              Optional[str] = None
    grip_size:                  Optional[str] = None
    grip_material:              Optional[str] = None
    shaft_material:             Optional[str] = None
    shaft_flexibility:          Optional[str] = None
    overall_length:             Optional[str] = None
    strung_weight:              Optional[str] = None
    unstrung_weight:            Optional[str] = None
    swing_weight:               Optional[str] = None
    recommended_playing_level:  Optional[str] = None
    playing_style:              Optional[str] = None
    cover_included:             Optional[str] = None
    warranty:                   Optional[str] = None
    country_of_origin:          Optional[str] = None

class TreadmillSpecs(BaseModel):
    motor_type:                 Optional[str] = None
    motor_power_continuous_hp:  Optional[str] = None
    motor_power_peak_hp:        Optional[str] = None
    speed_range:                Optional[str] = None
    incline_range:              Optional[str] = None
    decline_range:              Optional[str] = None
    running_belt_size:          Optional[str] = None
    deck_cushioning_system:     Optional[str] = None
    folding:                    Optional[str] = None
    assembled_dimensions:       Optional[str] = None
    folded_dimensions:          Optional[str] = None
    weight_capacity:            Optional[str] = None
    unit_weight:                Optional[str] = None
    display_type:               Optional[str] = None
    display_size:               Optional[str] = None
    console_features:           Optional[str] = None
    heart_rate_monitoring:      Optional[str] = None
    preset_programs:            Optional[str] = None
    connectivity:               Optional[str] = None
    app_compatibility:          Optional[str] = None
    speaker_system:             Optional[str] = None
    usb_charging_port:          Optional[str] = None
    fan:                        Optional[str] = None
    water_bottle_holder:        Optional[str] = None
    safety_key:                 Optional[str] = None
    transportation_wheels:      Optional[str] = None
    power_requirements:         Optional[str] = None
    warranty_frame:             Optional[str] = None
    warranty_motor:             Optional[str] = None
    warranty_parts:             Optional[str] = None
    warranty_labor:             Optional[str] = None
    certifications:             Optional[str] = None
    country_of_origin:          Optional[str] = None

class ExerciseBikeSpecs(BaseModel):
    bike_type:              Optional[str] = None
    resistance_type:        Optional[str] = None
    resistance_levels:      Optional[str] = None
    drive_system:           Optional[str] = None
    flywheel_weight:        Optional[str] = None
    seat_type:              Optional[str] = None
    seat_adjustability:     Optional[str] = None
    handlebar_type:         Optional[str] = None
    handlebar_adjustability:Optional[str] = None
    pedal_type:             Optional[str] = None
    display_type:           Optional[str] = None
    display_metrics:        Optional[str] = None
    heart_rate_monitoring:  Optional[str] = None
    preset_programs:        Optional[str] = None
    connectivity:           Optional[str] = None
    app_compatibility:      Optional[str] = None
    assembled_dimensions:   Optional[str] = None
    weight_capacity:        Optional[str] = None
    unit_weight:            Optional[str] = None
    transportation_wheels:  Optional[str] = None
    leveling_feet:          Optional[str] = None
    power_source:           Optional[str] = None
    warranty:               Optional[str] = None
    country_of_origin:      Optional[str] = None

class DumbbellSpecs(BaseModel):
    weight:                 Optional[str] = None
    weight_range:           Optional[str] = None
    weight_increment:       Optional[str] = None
    material:               Optional[str] = None
    coating:                Optional[str] = None
    handle_material:        Optional[str] = None
    handle_diameter:        Optional[str] = None
    handle_texture:         Optional[str] = None
    shape:                  Optional[str] = None
    overall_length:         Optional[str] = None
    overall_width:          Optional[str] = None
    head_diameter:          Optional[str] = None
    sold_as:                Optional[str] = None
    set_contents:           Optional[str] = None
    storage_rack_included:  Optional[str] = None
    warranty:               Optional[str] = None
    country_of_origin:      Optional[str] = None

class YogaMatSpecs(BaseModel):
    material:               Optional[str] = None
    thickness:              Optional[str] = None
    length:                 Optional[str] = None
    width:                  Optional[str] = None
    weight:                 Optional[str] = None
    texture:                Optional[str] = None
    non_slip_surface:       Optional[str] = None
    non_slip_bottom:        Optional[str] = None
    density:                Optional[str] = None
    cushioning_level:       Optional[str] = None
    eco_friendly:           Optional[str] = None
    latex_free:             Optional[str] = None
    carrying_strap_included:Optional[str] = None
    carry_bag_included:     Optional[str] = None
    care_instructions:      Optional[str] = None
    color_options:          Optional[str] = None
    warranty:               Optional[str] = None
    country_of_origin:      Optional[str] = None

class ResistanceBandSpecs(BaseModel):
    band_type:              Optional[str] = None
    resistance_level:       Optional[str] = None
    resistance_range:       Optional[str] = None
    material:               Optional[str] = None
    length:                 Optional[str] = None
    width:                  Optional[str] = None
    number_of_bands:        Optional[str] = None
    handle_type:            Optional[str] = None
    anchor_included:        Optional[str] = None
    ankle_strap_included:   Optional[str] = None
    carry_bag_included:     Optional[str] = None
    recommended_exercises:  Optional[str] = None
    warranty:               Optional[str] = None
    country_of_origin:      Optional[str] = None

class GeneralFitnessSpecs(BaseModel):
    product_type:           Optional[str] = None
    material:               Optional[str] = None
    dimensions:             Optional[str] = None
    weight:                 Optional[str] = None
    weight_capacity:        Optional[str] = None
    technical_specifications:Optional[str]= None
    included_accessories:   Optional[str] = None
    assembly_required:      Optional[str] = None
    warranty:               Optional[str] = None
    country_of_origin:      Optional[str] = None


# ── Union type for specifications ────────────────────────────────────────────

Specifications = (
    PickleballPaddleSpecs
    | TennisRacketSpecs
    | TreadmillSpecs
    | ExerciseBikeSpecs
    | DumbbellSpecs
    | YogaMatSpecs
    | ResistanceBandSpecs
    | GeneralFitnessSpecs
)


# ── Root output model ────────────────────────────────────────────────────────

class ProductOutput(BaseModel):
    product_identity:    ProductIdentity
    breadcrumbs:         list[str]                    # max 5 levels
    images:              ImagesOutput                 # three-array structure
    pricing:             Pricing
    stock_status:        StockStatus
    value_badges:        list[str]                    # e.g. ["Free Shipping", "USAPA Approved"]
    short_description:   str                          # max 200 chars
    long_description:    str                          # max 800 chars
    about_this_item:     list[str]                    # 3-6 bullet strings
    key_features:        list[KeyFeature]             # max 6
    features_table:      list[FeatureTableEntry]      # max 8
    specifications:      dict                         # category-specific, nulls for missing
    faqs:                list[FAQ]                     # min 5, max 8
    enrichment_metadata: EnrichmentMetadata

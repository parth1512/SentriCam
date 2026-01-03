"""
Telegram Bot Service for Vehicle Registration and Notifications
Handles user registration, commands, and sends vehicle activity alerts
"""
import os
import logging
import threading
from typing import Dict, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Configure logging
logger = logging.getLogger(__name__)

# Registration conversation states
(WAITING_FOR_NAME, WAITING_FOR_PHONE, WAITING_FOR_VEHICLE) = range(3)

class TelegramBot:
    """Telegram bot for vehicle registration and notifications"""
    
    def __init__(self, bot_token: str, flask_app):
        """
        Initialize Telegram bot
        
        Args:
            bot_token: Telegram bot token
            flask_app: Flask application instance (for database access)
        """
        self.bot_token = bot_token
        self.flask_app = flask_app
        self.application = None
        self.running = False
        self._bot_loop = None  # Store reference to bot's event loop
        
        # Temporary storage for registration data
        self.registration_data = {}
    
    def initialize(self):
        """Initialize and configure the bot"""
        if not self.bot_token:
            logger.warning("Telegram bot token not provided")
            return False
        
        try:
            self.application = Application.builder().token(self.bot_token).build()
            self._register_handlers()
            logger.info("Telegram bot initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    def _register_handlers(self):
        """Register all command and message handlers"""
        # Add error handler first to catch any unhandled errors
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Log the error and send a message to the user"""
            logger.error(f"Exception while handling an update: {context.error}")
            print(f"❌ Bot error: {context.error}")
            import traceback
            traceback.print_exc()
            
            # Try to send error message if update is available
            if isinstance(update, Update) and update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        "❌ An error occurred. Please try again with /register"
                    )
                except:
                    pass
        
        self.application.add_error_handler(error_handler)
        
        # Registration conversation handler
        registration_handler = ConversationHandler(
            entry_points=[CommandHandler('register', self.start_registration)],
            states={
                WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_name)],
                WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_phone)],
                WAITING_FOR_VEHICLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vehicle)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_registration)],
            name="registration_conversation",
            persistent=False,  # Don't persist across restarts
        )
        
        # IMPORTANT: Register ConversationHandler FIRST, before other handlers
        # This ensures it can catch messages in conversation states
        self.application.add_handler(registration_handler)
        logger.info("Registration conversation handler registered")
        print("✅ Registration handler registered")
        
        # Register other command handlers
        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler('myinfo', self.myinfo_command))
        self.application.add_handler(CommandHandler('testalert', self.testalert_command))
        self.application.add_handler(CommandHandler('remove', self.remove_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        
        # Add callback handler for remove confirmation
        from telegram.ext import CallbackQueryHandler
        self.application.add_handler(CallbackQueryHandler(self.handle_remove_callback, pattern="^remove_"))
        
        logger.info("All handlers registered successfully")
        print("✅ All bot handlers registered")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "👋 Hi there! Welcome to Campus Vehicle Tracker.\n\n"
            "I'll help you register your vehicle and send real-time location alerts "
            "whenever it's detected inside the campus.\n\n"
            "Type /register to begin registration."
        )
        await update.message.reply_text(welcome_message)
    
    async def start_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the registration process"""
        try:
            chat_id = str(update.effective_chat.id)
            logger.info(f"Starting registration for chat {chat_id}")
            print(f"📥 Bot received /register from chat {chat_id}")
            
            # Clear any previous registration data
            context.user_data.clear()
            if chat_id in self.registration_data:
                del self.registration_data[chat_id]
            
            # Check if user already has a registered vehicle
            with self.flask_app.app_context():
                from models import Vehicle
                existing = Vehicle.query.filter_by(telegram_chat_id=chat_id).first()
                
                if existing:
                    await update.message.reply_text(
                        f"⚠️ You already have a registered vehicle.\n\n"
                        f"👤 Name: {existing.name}\n"
                        f"📞 Phone: {existing.phone_number}\n"
                        f"🚗 Vehicle: {existing.vehicle_number}\n\n"
                        "To update your details, please use /remove first, then register again.\n"
                        "Or contact the admin for assistance."
                    )
                    print(f"⚠️ User {chat_id} already has vehicle {existing.vehicle_number}")
                    return ConversationHandler.END
            
            await update.message.reply_text(
                "📝 Let's register your vehicle!\n\n"
                "Please enter your full name:"
            )
            print(f"✅ Sent name request to {chat_id}")
            logger.info(f"Registration started for {chat_id}, waiting for name")
            return WAITING_FOR_NAME
            
        except Exception as e:
            logger.error(f"Error in start_registration: {e}")
            print(f"❌ Error in start_registration: {e}")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(
                    "❌ An error occurred. Please try again with /register"
                )
            except:
                pass
            return ConversationHandler.END
    
    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle name input"""
        try:
            chat_id = str(update.effective_chat.id)
            name = update.message.text.strip()
            
            logger.info(f"Received name input from {chat_id}: {name}")
            print(f"📥 Bot received name: {name} from chat {chat_id}")
            
            if not name or len(name) < 2:
                await update.message.reply_text("❌ Name is too short. Please enter your full name:")
                return WAITING_FOR_NAME
            
            # Store name in context.user_data (managed by ConversationHandler)
            context.user_data['name'] = name
            # Also store in instance for backup
            if chat_id not in self.registration_data:
                self.registration_data[chat_id] = {}
            self.registration_data[chat_id]['name'] = name
            
            logger.info(f"Stored name for {chat_id}: {name}")
            print(f"💾 Stored name: {name}")
            
            response_text = (
                f"Great! Hi {name}.\n\n"
                "Now, please enter your phone number (e.g., +91XXXXXXXXXX or 91XXXXXXXXXX):"
            )
            await update.message.reply_text(response_text)
            logger.info(f"Sent phone number request to {chat_id}")
            print(f"✅ Sent response to {chat_id}")
            return WAITING_FOR_PHONE
            
        except Exception as e:
            logger.error(f"Error in handle_name: {e}")
            print(f"❌ Error in handle_name: {e}")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(
                    "❌ An error occurred. Please try again with /register"
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {send_error}")
            return ConversationHandler.END
    
    async def handle_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number input"""
        try:
            chat_id = str(update.effective_chat.id)
            phone = update.message.text.strip()
            
            logger.info(f"Received phone input from {chat_id}: {phone}")
            print(f"📥 Bot received phone: {phone} from chat {chat_id}")
            
            # Basic phone validation
            phone_clean = phone.replace('+', '').replace('-', '').replace(' ', '')
            if not phone_clean.isdigit() or len(phone_clean) < 10:
                await update.message.reply_text(
                    "❌ Invalid phone number. Please enter a valid phone number (e.g., +91XXXXXXXXXX):"
                )
                return WAITING_FOR_PHONE
            
            # Store phone in context.user_data
            context.user_data['phone_number'] = phone
            # Also store in instance for backup
            if chat_id not in self.registration_data:
                self.registration_data[chat_id] = {}
            self.registration_data[chat_id]['phone_number'] = phone
            
            logger.info(f"Stored phone for {chat_id}: {phone}")
            print(f"💾 Stored phone: {phone}")
            
            await update.message.reply_text(
                "Perfect! Now, please enter your vehicle registration number (e.g., MH20EE7598):"
            )
            logger.info(f"Sent vehicle number request to {chat_id}")
            print(f"✅ Sent response to {chat_id}")
            return WAITING_FOR_VEHICLE
            
        except Exception as e:
            logger.error(f"Error in handle_phone: {e}")
            print(f"❌ Error in handle_phone: {e}")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(
                    "❌ An error occurred. Please try again with /register"
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {send_error}")
            return ConversationHandler.END
    
    async def handle_vehicle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle vehicle number input and complete registration"""
        try:
            chat_id = str(update.effective_chat.id)
            vehicle_number = update.message.text.strip().upper()
            
            logger.info(f"Received vehicle number from {chat_id}: {vehicle_number}")
            print(f"📥 Bot received vehicle: {vehicle_number} from chat {chat_id}")
            
            # Validate vehicle number format (basic check)
            if len(vehicle_number) < 6:
                await update.message.reply_text(
                    "❌ Vehicle number seems too short. Please enter a valid registration number (e.g., MH20EE7598):"
                )
                return WAITING_FOR_VEHICLE
            
            # Get stored registration data from context.user_data first, then fallback to instance
            name = context.user_data.get('name') or self.registration_data.get(chat_id, {}).get('name')
            phone = context.user_data.get('phone_number') or self.registration_data.get(chat_id, {}).get('phone_number')
            
            if not name or not phone:
                await update.message.reply_text(
                    "❌ Registration data incomplete. Please start again with /register"
                )
                if chat_id in self.registration_data:
                    del self.registration_data[chat_id]
                context.user_data.clear()
                return ConversationHandler.END
        
            # Check if vehicle number already exists and create new record
            with self.flask_app.app_context():
                from models import Vehicle, db
                existing_vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number).first()
                
                if existing_vehicle:
                    await update.message.reply_text(
                        f"❌ This vehicle number ({vehicle_number}) is already registered.\n\n"
                        "If this is your vehicle, please contact the admin.\n"
                        "Otherwise, please check your vehicle number and try again."
                    )
                    if chat_id in self.registration_data:
                        del self.registration_data[chat_id]
                    context.user_data.clear()
                    return ConversationHandler.END
                
                # Create new vehicle record
                try:
                    vehicle = Vehicle(
                        name=name,
                        phone_number=phone,
                        vehicle_number=vehicle_number,
                        telegram_chat_id=chat_id
                    )
                    db.session.add(vehicle)
                    db.session.commit()
                    
                    # Clean up temporary data
                    if chat_id in self.registration_data:
                        del self.registration_data[chat_id]
                    context.user_data.clear()
                    
                    success_message = (
                        f"✅ Registration successful!\n\n"
                        f"👤 Name: {name}\n"
                        f"📞 Phone: {phone}\n"
                        f"🚗 Vehicle: {vehicle_number}\n\n"
                        "You'll now receive instant updates when your car enters, moves, or exits campus.\n\n"
                        "Use /myinfo to view your registration details."
                    )
                    await update.message.reply_text(success_message)
                    
                    logger.info(f"Vehicle registered: {vehicle_number} by chat_id {chat_id}")
                    print(f"✅ Vehicle registered: {vehicle_number} by {name}")
                    return ConversationHandler.END
                    
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error registering vehicle: {e}")
                    print(f"❌ Error registering vehicle: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Send detailed error message to user
                    error_msg = (
                        f"❌ Registration failed!\n\n"
                        f"Error: {str(e)}\n\n"
                        f"Your details:\n"
                        f"👤 Name: {name}\n"
                        f"📞 Phone: {phone}\n"
                        f"🚗 Vehicle: {vehicle_number}\n\n"
                        "Please try again with /register or contact the admin."
                    )
                    try:
                        await update.message.reply_text(error_msg)
                    except Exception as send_error:
                        logger.error(f"Error sending error message: {send_error}")
                        print(f"❌ Could not send error message: {send_error}")
                    
                    if chat_id in self.registration_data:
                        del self.registration_data[chat_id]
                    context.user_data.clear()
                    return ConversationHandler.END
                    
        except Exception as e:
            logger.error(f"Error in handle_vehicle: {e}")
            print(f"❌ Error in handle_vehicle: {e}")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(
                    "❌ An error occurred. Please try again with /register"
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {send_error}")
            return ConversationHandler.END
    
    async def cancel_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel registration process"""
        chat_id = str(update.effective_chat.id)
        if chat_id in self.registration_data:
            del self.registration_data[chat_id]
        await update.message.reply_text("❌ Registration cancelled.")
        return ConversationHandler.END
    
    async def myinfo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /myinfo command - show user's registration info"""
        chat_id = str(update.effective_chat.id)
        
        with self.flask_app.app_context():
            from models import Vehicle
            vehicle = Vehicle.query.filter_by(telegram_chat_id=chat_id).first()
            
            if not vehicle:
                await update.message.reply_text(
                    "❌ You don't have a registered vehicle.\n\n"
                    "Use /register to register your vehicle."
                )
                return
            
            info_message = (
                "👤 Your Registration Details:\n\n"
                f"👤 Name: {vehicle.name}\n"
                f"📞 Phone: {vehicle.phone_number}\n"
                f"🚗 Vehicle: {vehicle.vehicle_number}\n"
                f"📅 Registered: {vehicle.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await update.message.reply_text(info_message)
    
    async def testalert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /testalert command - send a test notification"""
        chat_id = str(update.effective_chat.id)
        
        with self.flask_app.app_context():
            from models import Vehicle
            vehicle = Vehicle.query.filter_by(telegram_chat_id=chat_id).first()
            
            if not vehicle:
                await update.message.reply_text(
                    "❌ You don't have a registered vehicle.\n\n"
                    "Use /register to register your vehicle first."
                )
                return
            
            # Send test notification
            test_message = (
                "🧪 Test Alert\n\n"
                f"🚗 Your vehicle {vehicle.vehicle_number} was detected.\n"
                "📍 Location: Test Camera Location\n"
                "🕒 Time: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n"
                "This is a test notification. Your alerts are working correctly!"
            )
            await update.message.reply_text(test_message)
    
    async def remove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove command - remove user's vehicle registration"""
        chat_id = str(update.effective_chat.id)
        
        with self.flask_app.app_context():
            from models import Vehicle
            vehicle = Vehicle.query.filter_by(telegram_chat_id=chat_id).first()
            
            if not vehicle:
                await update.message.reply_text(
                    "❌ You don't have a registered vehicle to remove."
                )
                return
            
            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, remove", callback_data=f"remove_yes_{vehicle.id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="remove_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ Are you sure you want to remove your registration?\n\n"
                f"Vehicle: {vehicle.vehicle_number}\n"
                f"Name: {vehicle.name}\n\n"
                "You will stop receiving alerts after removal.",
                reply_markup=reply_markup
            )
    
    async def handle_remove_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle remove confirmation callback"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "remove_no":
            await query.edit_message_text("❌ Removal cancelled.")
            return
        
        if query.data.startswith("remove_yes_"):
            vehicle_id = int(query.data.split("_")[2])
            chat_id = str(update.effective_chat.id)
            
            with self.flask_app.app_context():
                from models import Vehicle, db
                vehicle = Vehicle.query.filter_by(id=vehicle_id, telegram_chat_id=chat_id).first()
                
                if vehicle:
                    vehicle_number = vehicle.vehicle_number
                    db.session.delete(vehicle)
                    db.session.commit()
                    await query.edit_message_text(
                        f"✅ Your vehicle ({vehicle_number}) has been removed.\n\n"
                        "You will no longer receive alerts.\n"
                        "Use /register to register again."
                    )
                    logger.info(f"Vehicle removed: {vehicle_number} by chat_id {chat_id}")
                else:
                    await query.edit_message_text("❌ Vehicle not found.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "📚 Available Commands:\n\n"
            "/start - Welcome message\n"
            "/register - Register your vehicle\n"
            "/myinfo - View your registration details\n"
            "/testalert - Send a test notification\n"
            "/remove - Remove your vehicle registration\n"
            "/help - Show this help message\n\n"
            "For support, contact the admin."
        )
        await update.message.reply_text(help_message)
    
    def send_notification(self, chat_id: str, message: str, location: Optional[Dict] = None) -> bool:
        """
        Send a notification message to a user
        
        Args:
            chat_id: Telegram chat ID
            message: Message text
            location: Optional location dict with 'lat' and 'lng'
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.application:
            logger.warning("Bot not initialized, cannot send notification")
            return False
        
        try:
            import asyncio
            
            async def send():
                try:
                    # Send text message
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Send location if provided
                    if location and location.get('lat') and location.get('lng'):
                        await self.application.bot.send_location(
                            chat_id=chat_id,
                            latitude=location['lat'],
                            longitude=location['lng']
                        )
                    
                    return True
                except Exception as e:
                    logger.error(f"Error sending Telegram notification: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            
            # Try to get the bot's event loop from the application
            # The bot runs in a separate thread with its own event loop
            bot_loop = None
            
            # Try multiple ways to get the bot's event loop
            if self.application:
                try:
                    # Method 1: Try to get from updater's network loop
                    if hasattr(self.application, 'updater') and self.application.updater:
                        updater = self.application.updater
                        # Check various internal attributes where the loop might be stored
                        if hasattr(updater, '_network_loop'):
                            bot_loop = updater._network_loop
                        elif hasattr(updater, '_event_loop'):
                            bot_loop = updater._event_loop
                        # Try to get from the bot's _event_loop
                        elif hasattr(self.application.bot, '_event_loop'):
                            bot_loop = self.application.bot._event_loop
                except Exception as e:
                    logger.debug(f"Could not get event loop from application: {e}")
            
            # Try stored loop reference
            if not bot_loop:
                bot_loop = self._bot_loop
            
            # If we found a running bot event loop, use it (thread-safe)
            if bot_loop and bot_loop.is_running() and not bot_loop.is_closed():
                try:
                    logger.debug(f"Using bot's event loop to send notification")
                    # Schedule coroutine on bot's event loop (thread-safe)
                    future = asyncio.run_coroutine_threadsafe(send(), bot_loop)
                    result = future.result(timeout=15.0)  # 15 second timeout
                    return result
                except Exception as e:
                    logger.warning(f"Error scheduling on bot event loop: {e}, trying fallback")
                    import traceback
                    traceback.print_exc()
                    # Fall through to fallback method
            
            # Fallback: Create a new bot instance with its own event loop
            # This is necessary when the bot's event loop is not accessible
            # This approach avoids event loop conflicts by using a separate bot instance
            logger.info("Creating temporary bot instance for notification (bot event loop not accessible)")
            try:
                # Create a new Bot instance just for sending (has its own HTTP client and event loop)
                from telegram import Bot
                temp_bot = Bot(token=self.bot_token)
                
                async def send_with_temp_bot():
                    try:
                        await temp_bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        if location and location.get('lat') and location.get('lng'):
                            await temp_bot.send_location(
                                chat_id=chat_id,
                                latitude=location['lat'],
                                longitude=location['lng']
                            )
                        
                        return True
                    except Exception as e:
                        logger.error(f"Error sending with temp bot: {e}")
                        import traceback
                        traceback.print_exc()
                        return False
                    finally:
                        # Clean up the temporary bot's HTTP session
                        try:
                            if hasattr(temp_bot, '_request') and hasattr(temp_bot._request, '_client_session'):
                                await temp_bot._request._client_session.close()
                        except Exception:
                            pass
                
                # Use asyncio.run() for the temporary bot (creates new event loop)
                # This is safe because we're using a separate bot instance
                result = asyncio.run(send_with_temp_bot())
                return result
                
            except Exception as temp_bot_error:
                logger.error(f"Error with temporary bot: {temp_bot_error}")
                import traceback
                traceback.print_exc()
                return False
                    
        except Exception as e:
            logger.error(f"Error in send_notification: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _send_sync(self, chat_id: str, message: str, location: Optional[Dict] = None) -> bool:
        """Synchronous wrapper for sending notifications (fallback method)"""
        import asyncio
        
        async def send():
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                if location and location.get('lat') and location.get('lng'):
                    await self.application.bot.send_location(
                        chat_id=chat_id,
                        latitude=location['lat'],
                        longitude=location['lng']
                    )
                
                return True
            except Exception as e:
                logger.error(f"Error in _send_sync: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # Use asyncio.run() which properly handles event loop lifecycle
        try:
            result = asyncio.run(send())
            return result
        except Exception as e:
            logger.error(f"Error in _send_sync: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_vehicle_event(self, vehicle_number: str, event_type: str, 
                          camera_name: str = None, location: Optional[Dict] = None, 
                          path: str = None, timestamp: str = None, include_location: bool = True) -> bool:
        """
        Send vehicle event notification
        
        Args:
            vehicle_number: Vehicle registration number
            event_type: 'entry', 'movement', 'exit', 'last_seen'
            camera_name: Name of the camera location
            location: Location dict with 'lat' and 'lng'
            path: Movement path (for movement events)
            timestamp: Event timestamp
            include_location: Whether to include location info (for first entry, set to False)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get vehicle and chat_id from database
            with self.flask_app.app_context():
                from models import Vehicle
                normalized_plate = vehicle_number.upper().strip()
                
                logger.info(f"🔍 Looking up vehicle {normalized_plate} in database for {event_type} notification")
                print(f"   🔍 Looking up vehicle {normalized_plate} in database...")
                
                try:
                    vehicle = Vehicle.query.filter_by(vehicle_number=normalized_plate).first()
                except Exception as db_error:
                    logger.error(f"❌ Database query error for vehicle {normalized_plate}: {db_error}")
                    print(f"   ❌ Database query error: {db_error}")
                    import traceback
                    traceback.print_exc()
                    return False
                
                if not vehicle:
                    logger.warning(f"❌ Vehicle {normalized_plate} not found in database")
                    print(f"   ❌ Vehicle {normalized_plate} not registered in database")
                    print(f"   💡 Vehicle must be registered in the system first")
                    return False
                
                if not vehicle.telegram_chat_id:
                    logger.warning(f"❌ No Telegram chat ID for vehicle {normalized_plate}")
                    print(f"   ❌ Vehicle {normalized_plate} has no Telegram chat ID linked")
                    print(f"   💡 User needs to register via Telegram bot first")
                    print(f"   💡 User should send /start to the Telegram bot and link their vehicle")
                    return False
                
                chat_id = vehicle.telegram_chat_id
                user_name = vehicle.name or "Unknown"
                logger.info(f"✅ Found vehicle {normalized_plate}: {user_name} (chat_id: {chat_id})")
                print(f"   ✅ Vehicle {normalized_plate} found: {user_name} (chat_id: {chat_id})")
                print(f"   📤 Preparing to send {event_type} notification...")
        except Exception as e:
            logger.error(f"❌ Error accessing database for vehicle {vehicle_number}: {e}")
            print(f"   ❌ Error accessing database: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Helper function to format timestamp in IST
        def format_timestamp(ts):
            """Format ISO timestamp to user-friendly format in IST (UTC+5:30)"""
            from datetime import timezone, timedelta
            
            # IST timezone offset (UTC+5:30)
            IST = timezone(timedelta(hours=5, minutes=30))
            
            if not ts:
                # Use current time in IST
                now = datetime.now(IST)
                return now.strftime('%I:%M %p IST on %d %b %Y')
            
            try:
                # Handle various timestamp formats
                ts_clean = ts.replace('Z', '+00:00')
                if '+' in ts_clean or ts_clean.endswith('+00:00'):
                    # Has timezone info - parse and convert to IST
                    dt = datetime.fromisoformat(ts_clean)
                    # Convert to IST if dt is timezone-aware
                    if dt.tzinfo is not None:
                        dt_ist = dt.astimezone(IST)
                    else:
                        # Assume UTC if no timezone info
                        dt_utc = dt.replace(tzinfo=timezone.utc)
                        dt_ist = dt_utc.astimezone(IST)
                elif 'T' in ts_clean:
                    # ISO format without timezone - assume UTC and convert to IST
                    dt = datetime.fromisoformat(ts_clean)
                    dt_utc = dt.replace(tzinfo=timezone.utc)
                    dt_ist = dt_utc.astimezone(IST)
                else:
                    # Try parsing as-is, assume UTC
                    dt = datetime.fromisoformat(ts_clean)
                    dt_utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                    dt_ist = dt_utc.astimezone(IST)
                
                # Format: "05:28 PM IST on 09 Nov 2025"
                formatted_time = dt_ist.strftime('%I:%M %p')  # e.g., "05:28 PM"
                formatted_date = dt_ist.strftime('%d %b %Y')  # e.g., "09 Nov 2025"
                return f"{formatted_time} IST on {formatted_date}"
            except Exception as e:
                # Fallback: return original timestamp if parsing fails
                logger.warning(f"Failed to parse timestamp {ts}: {e}")
                return ts
        
        # Format message based on event type
        if event_type == 'entry':
            time_str = format_timestamp(timestamp)
            
            if include_location:
                # Entry with location (legacy or subsequent entry)
                message = (
                    f"🚘 *Vehicle Entry Alert*\n\n"
                    f"Your vehicle *{vehicle_number}* has entered the campus.\n\n"
                    f"📍 *Location:* {camera_name or 'Camera'}\n"
                    f"🕒 *Time:* {time_str}"
                )
            else:
                # First entry - no location info (cleaner, more user-friendly message)
                message = (
                    f"🚘 *Vehicle Entry Alert*\n\n"
                    f"Your vehicle *{vehicle_number}* has entered the campus.\n\n"
                    f"🕒 *Detected at:* {time_str}\n\n"
                    f"📍 Location details will be shared once the vehicle moves to a different area."
                )
                # Don't send location for first entry
                location = None
        elif event_type == 'movement':
            time_str = format_timestamp(timestamp)
            path_text = path if path else f"{camera_name or 'Camera'}"
            message = (
                f"🚗 *Vehicle Movement*\n\n"
                f"Your vehicle *{vehicle_number}* has moved.\n\n"
                f"📍 *Path:* {path_text}\n"
                f"🕒 *Time:* {time_str}"
            )
        elif event_type == 'exit':
            time_str = format_timestamp(timestamp)
            message = (
                f"🚪 *Vehicle Exit*\n\n"
                f"Your vehicle *{vehicle_number}* has exited the campus.\n\n"
                f"📍 *Location:* {camera_name or 'Camera'}\n"
                f"🕒 *Time:* {time_str}"
            )
        elif event_type == 'last_seen':
            time_str = format_timestamp(timestamp)
            
            maps_link = ""
            if location and location.get('lat') and location.get('lng'):
                lat = location['lat']
                lng = location['lng']
                # Google Maps link with 50m radius circle
                # Using the radius parameter in the URL
                maps_link = f"\n\n🗺️ [📍 View Location on Google Maps (50m radius)](https://www.google.com/maps/search/?api=1&query={lat},{lng})"
            
            location_text = f"near *{camera_name}*" if camera_name else "on campus"
            message = (
                f"📍 *Last Seen Update*\n\n"
                f"Your vehicle *{vehicle_number}* was last seen {location_text}.\n\n"
                f"📏 *Estimated Range:* 50 meters\n"
                f"🕒 *Time:* {time_str}"
                f"{maps_link}"
            )
        else:
            message = f"🚗 Vehicle {vehicle_number} activity detected at {camera_name or 'Camera'}"
        
        # Send notification (only include location if include_location is True and location exists)
        send_location = location if include_location and location else None
        
        logger.info(f"📤 Sending {event_type} notification to chat_id {chat_id} for vehicle {normalized_plate}")
        print(f"   📤 Sending notification to Telegram (chat_id: {chat_id})...")
        
        try:
            result = self.send_notification(chat_id, message, send_location)
            if result:
                logger.info(f"✅ Successfully sent {event_type} notification for vehicle {normalized_plate}")
                print(f"   ✅ Notification sent successfully to Telegram")
            else:
                logger.error(f"❌ Failed to send {event_type} notification for vehicle {normalized_plate}")
                print(f"   ❌ Failed to send notification to Telegram")
            return result
        except Exception as e:
            logger.error(f"❌ Exception sending notification for vehicle {normalized_plate}: {e}")
            print(f"   ❌ Exception sending notification: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_polling(self):
        """Start the bot in polling mode - this runs in a separate thread"""
        if not self.application:
            logger.error("Bot not initialized, cannot start polling")
            print("❌ Telegram Bot: Not initialized, cannot start polling")
            return
        
        try:
            self.running = True
            logger.info("Starting Telegram bot polling...")
            print("🔄 Telegram Bot: Starting polling in thread...")
            print("   Bot will now listen for messages from Telegram")
            print("   ⚠️  Make sure only ONE instance is running!")
            
            # run_polling() is the correct way - it's blocking and handles everything
            # This will run until the application is stopped
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False,  # Don't drop pending updates
                stop_signals=None,  # Don't handle signals in thread
                close_loop=False
            )
            
        except KeyboardInterrupt:
            logger.info("Bot polling interrupted")
            print("🛑 Telegram Bot: Polling interrupted")
            self.running = False
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in bot polling: {e}")
            print(f"❌ Telegram Bot polling error: {e}")
            
            # Check for conflict error
            if "Conflict" in error_msg or "getUpdates" in error_msg:
                print("⚠️  CONFLICT DETECTED: Another bot instance is running!")
                print("   Please stop all other bot instances and restart.")
                print("   Run: pkill -f 'python.*app.py'")
            
            import traceback
            traceback.print_exc()
            self.running = False
            # Don't auto-restart on conflict - user needs to fix it manually
            if "Conflict" not in error_msg:
                print("   Will attempt to restart polling in 5 seconds...")
                import time
                time.sleep(5)
                if self.running:
                    self.start_polling()
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        if self.application:
            try:
                self.application.updater.stop()
                self.application.stop()
                logger.info("Telegram bot stopped")
                print("🛑 Telegram Bot: Stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
                print(f"⚠️  Error stopping bot: {e}")

# Global bot instance
_telegram_bot = None

def get_telegram_bot(bot_token: str = None, flask_app=None) -> Optional[TelegramBot]:
    """Get or create Telegram bot instance"""
    global _telegram_bot
    
    if _telegram_bot:
        return _telegram_bot
    
    if not bot_token:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    if not bot_token:
        return None
    
    if not flask_app:
        return None
    
    try:
        _telegram_bot = TelegramBot(bot_token, flask_app)
        if _telegram_bot.initialize():
            return _telegram_bot
    except Exception as e:
        logger.error(f"Error creating Telegram bot: {e}")
        import traceback
        traceback.print_exc()
    
    return None

def start_bot_thread(bot_token: str = None, flask_app=None):
    """Start bot in a separate thread"""
    if not bot_token:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    if not bot_token:
        logger.warning("Telegram bot token not found")
        print("⚠️  Telegram Bot: Token not found")
        return None
    
    if not flask_app:
        logger.warning("Flask app not provided")
        print("⚠️  Telegram Bot: Flask app not provided")
        return None
    
    try:
        bot = get_telegram_bot(bot_token, flask_app)
        if bot:
            # Create thread with better error handling
            def run_bot():
                try:
                    bot.start_polling()
                except Exception as e:
                    logger.error(f"Bot thread error: {e}")
                    print(f"❌ Telegram Bot thread error: {e}")
                    import traceback
                    traceback.print_exc()
            
            thread = threading.Thread(target=run_bot, daemon=True, name="TelegramBot")
            thread.start()
            logger.info("Telegram bot thread started")
            print(f"✅ Telegram Bot: Thread started (daemon={thread.daemon})")
            
            # Give thread a moment to start
            import time
            time.sleep(0.5)
            
            # Check if thread is still alive
            if not thread.is_alive():
                print("⚠️  Telegram Bot: Thread died immediately after start")
                return None
            
            return bot
        else:
            print("⚠️  Telegram Bot: Failed to create bot instance")
            return None
    except Exception as e:
        logger.error(f"Error starting bot thread: {e}")
        print(f"❌ Telegram Bot: Error starting thread: {e}")
        import traceback
        traceback.print_exc()
        return None


#import <Lynx/LynxUI.h>

NS_ASSUME_NONNULL_BEGIN

@interface LynxTextField : UITextField

@property(nonatomic, assign) UIEdgeInsets padding;

@end

@interface LynxExplorerInput : LynxUI <LynxTextField *> <UITextFieldDelegate>

@end

NS_ASSUME_NONNULL_END